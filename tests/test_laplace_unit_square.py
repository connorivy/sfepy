# 30.05.2007, c
# last revision: 25.02.2008
from __future__ import absolute_import
from sfepy import data_dir
import six

filename_mesh = data_dir + '/meshes/2d/square_unit_tri.mesh'

material_1 = {
    'name' : 'coef',
    'values' : {
        'val' : 1.0,
    },
}
material_2 = {
    'name' : 'm',
    'values' : {
        'K' : [[1.0, 0.0], [0.0, 1.0]],
    },
}

field_1 = {
    'name' : 'a_harmonic_field',
    'dtype' : 'real',
    'shape' : 'scalar',
    'region' : 'Omega',
    'approx_order' : 2,
}

variable_1 = {
    'name' : 't',
    'kind' : 'unknown field',
    'field' : 'a_harmonic_field',
    'order' : 0,
}
variable_2 = {
    'name' : 's',
    'kind' : 'test field',
    'field' : 'a_harmonic_field',
    'dual' : 't',
}

region_1000 = {
    'name' : 'Omega',
    'select' : 'all',
}

region_1 = {
    'name' : 'Left',
    'select' : 'vertices in (x < -0.499)',
    'kind' : 'facet',
}
region_2 = {
    'name' : 'Right',
    'select' : 'vertices in (x > 0.499)',
    'kind' : 'facet',
}
region_3 = {
    'name' : 'Gamma',
    'select' : 'vertices of surface',
    'kind' : 'facet',
}

ebc_1 = {
    'name' : 't_left',
    'region' : 'Left',
    'dofs' : {'t.0' : 5.0},
}
ebc_2 = {
    'name' : 't_right',
    'region' : 'Right',
    'dofs' : {'t.0' : 0.0},
}
#    'Left' : ('T3', (30,), 'linear_y'),

integral_1 = {
    'name' : 'i',
    'order' : 2,
}

equations = {
    'Temperature' : """dw_laplace.i.Omega( coef.val, s, t ) = 0"""
}

solution = {
    't' : '- 5.0 * (x - 0.5)',
}

solver_0 = {
    'name' : 'ls',
    'kind' : 'ls.scipy_direct',
}

solver_1 = {
    'name' : 'newton',
    'kind' : 'nls.newton',

    'i_max'      : 1,
    'eps_a'      : 1e-10,
}

lin_min, lin_max = 0.0, 2.0

##
# 31.05.2007, c
def linear( bc, ts, coor, which ):
    vals = coor[:,which]
    min_val, max_val = vals.min(), vals.max()
    vals = (vals - min_val) / (max_val - min_val) * (lin_max - lin_min) + lin_min
    return vals

##
# 31.05.2007, c
def linear_x( bc, ts, coor ):
    return linear( bc, ts, coor, 0 )
def linear_y( bc, ts, coor ):
    return linear( bc, ts, coor, 1 )
def linear_z( bc, ts, coor ):
    return linear( bc, ts, coor, 2 )

from sfepy.base.testing import TestCommon

##
# 30.05.2007, c
class Test( TestCommon ):

    ##
    # 30.05.2007, c
    def from_conf( conf, options ):
        from sfepy.applications import solve_pde

        problem, state = solve_pde(conf, save_results=False)

        test = Test(problem=problem, state=state, conf=conf, options=options)
        return test
    from_conf = staticmethod( from_conf )

    ##
    # 30.05.2007, c
    def test_solution( self ):
        sol = self.conf.solution
        vec = self.state()
        problem = self.problem

        variables = problem.get_variables()

        ok = True
        for var_name, expression in six.iteritems(sol):
            coor = variables[var_name].field.get_coor()
            ana_sol = self.eval_coor_expression( expression, coor )
            num_sol = variables.get_vec_part(vec, var_name)
            ret = self.compare_vectors( ana_sol, num_sol,
                                       label1 = 'analytical %s' % var_name,
                                       label2 = 'numerical %s' % var_name )
            if not ret:
                self.report( 'variable %s: failed' % var_name )

            ok = ok and ret

        return ok

    ##
    # c: 30.05.2007, r: 19.02.2008
    def test_boundary_fluxes( self ):
        import os.path as op
        from sfepy.linalg import rotation_matrix2d
        from sfepy.discrete import Material
        problem = self.problem

        angles = [0, 30, 45]
        region_names = ['Left', 'Right', 'Gamma']
        values = [5.0, -5.0, 0.0]

        variables = problem.get_variables()
        get_state = variables.get_vec_part
        state = self.state.copy()

        problem.time_update(ebcs={}, epbcs={})
#        problem.save_ebc( 'aux.vtk' )

        state.apply_ebc()
        nls = problem.get_nls()
        aux = nls.fun(state())

        field = variables['t'].field

        conf_m = problem.conf.get_item_by_name('materials', 'm')
        m = Material.from_conf(conf_m, problem.functions)

        name = op.join( self.options.out_dir,
                        op.split( problem.domain.mesh.name )[1] + '_%02d.mesh' ) 

        orig_coors = problem.get_mesh_coors().copy()
        ok = True
        for ia, angle in enumerate( angles ):
            self.report( '%d: mesh rotation %d degrees' % (ia, angle) )
            problem.domain.mesh.transform_coors( rotation_matrix2d( angle ),
                                                 ref_coors = orig_coors )
            problem.set_mesh_coors(problem.domain.mesh.coors,
                                   update_fields=True)
            problem.domain.mesh.write( name % angle, io = 'auto' )
            for ii, region_name in enumerate( region_names ):
                flux_term = 'ev_surface_flux.i.%s( m.K, t )' % region_name
                val1 = problem.evaluate(flux_term, t=variables['t'], m=m)

                rvec = get_state( aux, 't', True )
                reg = problem.domain.regions[region_name]
                nods = field.get_dofs_in_region(reg, merge=True)
                val2 = rvec[nods].sum() # Assume 1 dof per node.

                ok = ok and ((abs( val1 - values[ii] ) < 1e-10) and
                             (abs( val2 - values[ii] ) < 1e-10))
                self.report( '  %d. %s: %e == %e == %e'\
                             % (ii, region_name, val1, val2, values[ii]) )

        # Restore original coordinates.
        problem.domain.mesh.transform_coors(rotation_matrix2d(0),
                                            ref_coors=orig_coors)
        problem.set_mesh_coors(problem.domain.mesh.coors,
                               update_fields=True)

        return ok
