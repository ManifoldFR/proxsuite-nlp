"""
Copyright (C) 2022 LAAS-CNRS, INRIA

Author:
    Wilson Jallet
"""
import proxnlp

import pinocchio as pin
import pinocchio.casadi as cpin

import numpy as np
import casadi as cas

import example_robot_data as erd
import matplotlib.pyplot as plt

from proxnlp.manifolds import MultibodyPhaseSpace, VectorSpace
from proxnlp.utils import CasadiFunction, plot_pd_errs

from tap import Tap


class Args(Tap):
    view: bool = False
    num_replay: int = 3
    record: bool = False
    video_file: str = "double_pendulum.mp4"

    def process_args(self):
        if self.record:
            self.view = True


args = Args().parse_args()
print(args)


USE_VIEWER = args.view
if USE_VIEWER:
    try:
        import meshcat_utils as msu
    except ImportError:
        import warnings

        warnings.warn(
            "Please install pin-meshcat-utils to record or use the Meshcat viewer."
        )
        raise

print("Package version: {}".format(proxnlp.__version__))
robot = erd.load("double_pendulum_simple")
# robot = erd.load("double_pendulum")
model = robot.model
rdata = model.createData()
toolid = model.getFrameId("link2")

Tf = 1.2
dt = 1.0 / 30
nsteps = int(Tf / dt)
Tf = nsteps * dt
print("Time horizon: {:.3g}".format(Tf))
print("Time step   : {:.3g}".format(dt))
print("No. of steps: {:d}".format(nsteps))

nq = model.nq
B = np.array([[0.0], [1.0]])
nu = B.shape[1]

xspace = MultibodyPhaseSpace(model)
pb_space = VectorSpace(nsteps * nu + (nsteps + 1) * (xspace.nx))

u_bound = 0.25
x0 = xspace.neutral()
theta0 = np.pi
x0[0] = theta0
xtarget = xspace.neutral()

print("Initial:", x0)
print("Final  :", xtarget)

if USE_VIEWER:
    vizer: pin.visualize.MeshcatVisualizer = pin.visualize.MeshcatVisualizer(
        model, robot.collision_model, robot.visual_model
    )
    vizer.initViewer(loadModel=True)
    vizer.display(x0[: model.nq])
    vizer.viewer.open()
    viz_util = msu.VizUtil(vizer)
    viz_util.set_cam_angle_preset("acrobot")


def make_dynamics_expression(cmodel: cpin.Model, cdata: cpin.Data, x0, cxs, cus):
    resdls = [cxs[0] - x0]
    for t in range(nsteps):
        q = cxs[t][:nq]
        v = cxs[t][nq:]
        tau = B @ cus[t]
        acc = cpin.aba(cmodel, cdata, q, v, tau)
        vnext = v + dt * acc
        qnext = cpin.integrate(cmodel, q, dt * vnext)
        xnext = cas.vertcat(qnext, vnext)
        resdls.append(cxs[t + 1] - xnext)
    expression = cas.vertcat(*resdls)
    return expression


class MultipleShootingProblem:
    """Multiple-shooting formulation."""

    def __init__(self, x0, xtarget):
        self.cmodel = cpin.Model(model)
        self.cdata = self.cmodel.createData()
        cxs = [cas.SX.sym("x%i" % i, xspace.nx) for i in range(nsteps + 1)]
        cus = [cas.SX.sym("u%i" % i, nu) for i in range(nsteps)]
        cX_s = cas.vertcat(*cxs)
        cU_s = cas.vertcat(*cus)

        cXU_s = cas.vertcat(cX_s, cU_s)

        w_u = 1e-2
        w_x = 1e-3
        w_term = 2.0 * np.ones(xspace.ndx)
        w_term[2:] = 1e-3
        ferr = cxs[nsteps] - xtarget
        cost_expression = (
            0.5 * w_x * dt * cas.dot(cX_s, cX_s)
            + 0.5 * w_u * dt * cas.dot(cU_s, cU_s)
            + 0.5 * cas.dot(ferr, w_term * ferr)
        )

        self.cost_fun = CasadiFunction(
            pb_space.nx, pb_space.ndx, cost_expression, cXU_s, use_hessian=True
        )

        x0 = cas.SX(x0)
        expression = make_dynamics_expression(self.cmodel, self.cdata, x0, cxs, cus)
        self.dynamics_fun = CasadiFunction(
            pb_space.nx, pb_space.ndx, expression, cXU_s, use_hessian=False
        )

        control_bounds_ = []
        for t in range(nsteps):
            control_bounds_.append(cus[t] - u_bound)
            control_bounds_.append(-cus[t] - u_bound)
        control_expr = cas.vertcat(*control_bounds_)
        self.control_bound_fun = CasadiFunction(
            pb_space.nx, pb_space.ndx, control_expr, cXU_s, use_hessian=False
        )


probdef = MultipleShootingProblem(x0, xtarget)
cost_fun = proxnlp.costs.CostFromFunction(probdef.cost_fun)
dynamical_constraint = proxnlp.constraints.create_equality_constraint(
    probdef.dynamics_fun
)
bound_constraint = proxnlp.constraints.create_inequality_constraint(
    probdef.control_bound_fun
)

constraints_ = []
constraints_.append(dynamical_constraint)
constraints_.append(bound_constraint)
prob = proxnlp.Problem(cost_fun, constraints_)

print("No. of variables  :", pb_space.nx)
print("No. of constraints:", prob.total_constraint_dim)
workspace = proxnlp.Workspace(pb_space.nx, pb_space.ndx, prob)
results = proxnlp.Results(pb_space.nx, prob)

callback = proxnlp.helpers.HistoryCallback()
tol = 1e-5
rho_init = 1e-7
mu_init = 0.1
solver = proxnlp.Solver(
    pb_space, prob, mu_init=mu_init, rho_init=rho_init, tol=tol, verbose=proxnlp.VERBOSE
)
solver.register_callback(callback)
solver.maxiters = 600
solver.use_gauss_newton = True
solver.ls_strat = proxnlp.LinesearchStrategy.ARMIJO

xu_init = pb_space.neutral()
for t in range(nsteps + 1):
    xu_init[t * xspace.nx] = theta0
lams0 = [np.zeros(cs.nr) for cs in constraints_]
flag = solver.solve(workspace, results, xu_init, lams0)

print("Results struct:\n{}".format(results))
prim_errs = callback.storage.prim_infeas
dual_errs = callback.storage.dual_infeas

xus_opt = results.xopt
xs_opt_flat = xus_opt[: (nsteps + 1) * xspace.nx]
us_opt_flat = xus_opt[(nsteps + 1) * xspace.nx :]
us_opt = us_opt_flat.reshape(nsteps, -1)
xs_opt = xs_opt_flat.reshape(nsteps + 1, -1)
qs_opt = xs_opt[:, : model.nq]
vs_opt = xs_opt[:, model.nq :]

# Plotting

plt.style.use("seaborn-ticks")
plt.rcParams["lines.linewidth"] = 1.0
plt.rcParams["axes.linewidth"] = 1.0

times = np.linspace(0.0, Tf, nsteps + 1)
labels_ = ["$x_{%i}$" % i for i in range(model.nq)]

fig: plt.Figure = plt.figure(figsize=(10.8, 4.8))
gs0 = fig.add_gridspec(1, 3)

plt.subplot(gs0[0])
hlines_style = dict(alpha=0.7, ls="-", lw=2, zorder=-1)
lines = plt.plot(times, qs_opt)
cols_ = [li.get_color() for li in lines]
labels_ = ["$q_{0}$".format(i) for i in range(model.nq)]
hlines = plt.hlines(xtarget[: model.nq], *times[[0, -1]], colors=cols_, **hlines_style)

plt.legend(labels_)
plt.xlabel("Time $t$")
plt.title("Configuration $q$")

plt.subplot(gs0[1])
plt.plot(times[:-1], us_opt)
plt.hlines((-u_bound, u_bound), *times[[0, -2]], colors="k", **hlines_style)
plt.xlabel("Time $t$")
plt.title("Controls $u$")

gss = gs0[2].subgridspec(2, 1, height_ratios=[3, 1])
ax0 = plt.subplot(gss[0])
plot_pd_errs(ax0, prim_errs, dual_errs)

plt.subplot(gss[1])
plt.plot(callback.storage.alphas, c='gray', alpha=.8, marker='.', markersize=2)
plt.tight_layout()

# plot kkt matrix
fig, ax = plt.subplots()
kkt_mat = workspace.kkt_matrix.copy()
plt.imshow(kkt_mat.astype(bool), cmap=plt.cm.binary, vmin=0.)
ntot = pb_space.ndx
ptch = plt.Rectangle((0, 0), ntot, ntot)
ptch.set_facecolor('#19ff1d')
ptch.set_alpha(0.1)
ptch.set_edgecolor('none')
ptch.set_transform(ax.transData)
ax.add_patch(ptch)

plt.tight_layout()
plt.show()


if USE_VIEWER:
    viz_util.set_cam_angle_preset("acrobot")
    allimgs = []
    fps = 1.0 / dt
    recorder = msu.VideoRecorder(args.video_file, fps)
    for _ in range(args.num_replay):
        viz_util.play_trajectory(
            xs_opt,
            us_opt,
            frame_ids=[toolid],
            show_vel=True,
            timestep=dt,
            record=args.record,
            recorder=recorder)