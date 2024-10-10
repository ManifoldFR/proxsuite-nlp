#pragma once

#include "proxsuite-nlp/fwd.hpp"

namespace proxsuite {
namespace nlp {
namespace context {

using Scalar = double;

PROXSUITE_NLP_DYNAMIC_TYPEDEFS(Scalar);
using VectorXBool = Eigen::Matrix<bool, Eigen::Dynamic, 1>;

using BCLParams = ::proxsuite::nlp::BCLParamsTpl<Scalar>;
using Problem = ProblemTpl<Scalar>;
using Results = ResultsTpl<Scalar>;
using Workspace = WorkspaceTpl<Scalar>;
using Cost = CostFunctionBaseTpl<Scalar>;
using Constraint = ConstraintObjectTpl<Scalar>;
using ConstraintSet = ConstraintSetTpl<Scalar>;
using ConstraintBase PROXSUITE_NLP_DEPRECATED = ConstraintSetTpl<Scalar>;
using Function = BaseFunctionTpl<Scalar>;
using C1Function = C1FunctionTpl<Scalar>;
using C2Function = C2FunctionTpl<Scalar>;

using Manifold = ManifoldAbstractTpl<Scalar>;
using ProxNLPSolverTpl = ProxNLPSolverTpl<Scalar>;

// func pointer signatures
using VecFuncType = void(const ConstVectorRef &, VectorRef) const;
using MatFuncType = void(const ConstVectorRef &, MatrixRef) const;
using VHPFuncType = void(const ConstVectorRef &, const ConstVectorRef &,
                         MatrixRef) const;

// allocated func signatures
using VecFuncRetType = VectorXs(const ConstVectorRef &) const;
using MatFuncRetType = MatrixXs(const ConstVectorRef &) const;
using VHPFuncRetType = MatrixXs(const ConstVectorRef &,
                                const ConstVectorRef &) const;

} // namespace context
} // namespace nlp
} // namespace proxsuite
