/**
 * @file    Implements a function which is the residual between two points on the manifold,
 *          obtained by the manifold retraction op.
 */
#pragma once

#include "lienlp/function-base.hpp"
#include "lienlp/manifold-base.hpp"


namespace lienlp
{
  
  /**
   * Constraint function to be equal to a given element of a manifold.
   * This is templated on the manifold.
   */
  template<typename _Scalar>
  struct ManifoldDifferenceToPoint : C2Function<_Scalar>
  {
  public:
    using Scalar = _Scalar;
    LIENLP_FUNCTOR_TYPEDEFS(Scalar)

    using Base = C2Function<Scalar>;
    using Base::operator();
    using Base::computeJacobian;
    using M = ManifoldAbstractTpl<Scalar>;

    /// Target point on the manifold.
    typename M::PointType m_target;

    ManifoldDifferenceToPoint(const M& manifold, const ConstVectorRef& target)
      : Base(manifold.nx(), manifold.ndx(), manifold.ndx()),
          m_target(target),
          m_manifold(manifold)
        {}

    ReturnType operator()(const ConstVectorRef& x) const
    {
      return m_manifold.difference(m_target, x);
    }

    void computeJacobian(const ConstVectorRef& x, Eigen::Ref<JacobianType> Jout) const
    {
      m_manifold.Jdifference(m_target, x, Jout, 1);
    }

  private:
    const M& m_manifold;
  };

} // namespace lienlp

