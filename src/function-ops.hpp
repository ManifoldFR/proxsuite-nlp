#pragma once

#include "proxnlp/function-base.hpp"

#include <utility>


namespace proxnlp
{

  /** @brief Compose two functions.
   */
  template<typename _Scalar>
  struct ComposeFunctionTpl : C2FunctionTpl<_Scalar>
  {
  public:
    using Scalar = _Scalar;
    using Base = C2FunctionTpl<Scalar>;
    using Base::computeJacobian;
    using Base::vectorHessianProduct;

    PROXNLP_FUNCTOR_TYPEDEFS(Scalar)

    ComposeFunctionTpl(const Base& left, const Base& right)
      : Base(right.nx(), right.ndx(), left.nr())
      , left(left), right(right) {}

    ReturnType operator()(const ConstVectorRef& x) const
    {
      return left(right(x));
    }

    void computeJacobian(const ConstVectorRef& x, Eigen::Ref<JacobianType> Jout) const
    {
      left.computeJacobian(right(x), Jout);
      Jout = Jout * right.computeJacobian(x);
    }
  private:
    const Base& left;
    const Base& right;

  };
  
} // namespace proxnlp

