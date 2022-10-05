/* Copyright (C) 2022 LAAS-CNRS, INRIA
 */
#include "proxnlp/modelling/costs/squared-distance.hpp"
#include "proxnlp/modelling/residuals/linear.hpp"
#include "proxnlp/modelling/constraints/equality-constraint.hpp"
#include "proxnlp/modelling/spaces/vector-space.hpp"
#include "proxnlp/solver-base.hpp"

#include "example-base.hpp"

#include <Eigen/QR>

/**
 * Sample a random orthonormal matrix.
 */
template <typename Scalar>
Eigen::Matrix<Scalar, -1, -1> randomOrthogonal(int M, int N) {
  using MatrixXs = Eigen::Matrix<Scalar, -1, -1>;
  MatrixXs out = MatrixXs::Random(N, N);
  Eigen::FullPivHouseholderQR<Eigen::Ref<MatrixXs>> qr(out);
  Eigen::Matrix<Scalar, -1, -1> Q(qr.matrixQ());
  return Q.template topLeftCorner<-1, -1>(M, N);
}

using namespace proxnlp;
using Problem = ProblemTpl<double>;
using EqualityType = EqualityConstraint<double>;
using Constraint = ConstraintObject<double>;

template <int N, int M = 1> int submain() {
  using Manifold = VectorSpaceTpl<double>;
  auto space_ = std::make_shared<Manifold>(N);
  const Manifold &space = *space_;
  typename Manifold::PointType p1 = space.rand();

  Eigen::MatrixXd Qroot(N, N + 1);
  Qroot.setRandom();
  Eigen::MatrixXd Q_ = Qroot * Qroot.transpose() / N;

  Eigen::MatrixXd A(M, N);
  A.setZero();
  if (M > 0) {
    A = randomOrthogonal<double>(M, N);
  }
  Eigen::VectorXd b(M);
  b.setRandom();

  auto res1 = std::make_shared<LinearFunctionTpl<double>>(A, b);

  auto cost = std::make_shared<QuadraticDistanceCost<double>>(
      space_, space.neutral(), Q_);

  std::vector<Problem::ConstraintType> constraints;
  if (M > 0) {
    constraints.emplace_back(res1, std::make_shared<EqualityType>());
  }

  auto problem = std::make_shared<Problem>(space_, cost, constraints);

  using Solver_t = SolverTpl<double>;
  typename Solver_t::Workspace workspace(*problem);
  typename Solver_t::Results results(*problem);

  Solver_t solver(problem);
  solver.setPenalty(1e-4);
  solver.setProxParameter(1e-8);
  solver.use_gauss_newton = true;

  solver.solve(workspace, results, p1, workspace.lams_prev);
  fmt::print("{}\n", results);

  return 0;
}

int main() {
  submain<2>();
  submain<4>();
  submain<4, 3>();
  submain<10, 4>();
  submain<10, 6>();
  submain<20, 1>();
  submain<20, 4>();
  submain<50, 0>();
  submain<50, 10>();
  submain<100, 50>();
  submain<200, 42>();
  return 0;
}
