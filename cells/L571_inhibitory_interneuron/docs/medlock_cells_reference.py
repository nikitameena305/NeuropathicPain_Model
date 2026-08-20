import genrn
from neuron import h

# can use (EX)|(IN)|(PRO)cellRule with netpyne
# can use create(EX)|(IN)|(PRO)\(\) with netpyne or python+neuron

EXtonicRule  = {
 'conds': {},
 'globals': {},
 'secLists': {},
 'secs': {'dend': {'geom': {'L': 400.0, 'nseg': 5, 'diam': 3.0, 'Ra': 150.0, 'cm': 1.0}, 
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 2.0, 'depth': 0.1},
                             'HH2': {'gnabar': 0.0, 'gkbar': 0.036, 'vtraub': -55.0},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'borgka': {'gkabar': 0.0},
                             'KDRI': {'gkbar': 0.0},
                             'pas': {'g': 1.23e-06, 'e': -65.0}},
                   'topol': {'parentSec': 'soma', 'parentX': 0.0, 'childX': 0.0}},
          'hillock': {'geom': {'L': 9.0, 'nseg': 3, 'diam': 1.5, 'Ra': 150.0, 'cm': 1.0},
                      'ions': {'k': {'e': -77.0, 'i': 54.4, 'o': 2.5},
                               'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                      'mechs': {'B_Na': {'gnabar': 0.0, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                                'HH2': {'gkbar': 0.0036, 'gnabar': 5.45, 'vtraub': -55},
                                'borgka': {'gkabar': 0.0},
                                'KDRI': {'gkbar': 0.0},
                                'pas': {'g': 1.23e-06, 'e': -65.0}},
                      'topol': {'parentSec': 'soma', 'parentX': 1.0, 'childX': 0.0}},
          'soma': {'geom': {'L': 20.0, 'nseg': 3, 'diam': 20.0, 'Ra': 150.0, 'cm': 1.0},
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'B_Na': {'gnabar': 0.0, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                             'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 1.0, 'depth': 0.1},
                             'HH2': {'gkbar': 0.0002, 'gnabar': 0.0125, 'vtraub': -55},
                             'borgka': {'gkabar': 0.0},
                             'KDRI': {'gkbar': 0.0},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'pas': {'g': 1.23e-06, 'e': -65.0}},
                   'topol': {}}}
}

EXdelayedRule  = {
 'conds': {},
 'globals': {},
 'secLists': {},
 'secs': {'dend': {'geom': {'L': 400.0, 'nseg': 5, 'diam': 3.0, 'Ra': 150.0, 'cm': 1.0}, 
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 2.0, 'depth': 0.1},
                             'HH2': {'gnabar': 0.0, 'gkbar': 0.144, 'vtraub': -50.2},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'borgka': {'gkabar': 0.0009333},
                             'KDRI': {'gkbar': 0.96e-05},
                             'pas': {'g': 0.96e-06, 'e': -65.0}},
                   'topol': {'parentSec': 'soma', 'parentX': 0.0, 'childX': 0.0}},
          'hillock': {'geom': {'L': 9.0, 'nseg': 3, 'diam': 1.5, 'Ra': 150.0, 'cm': 1.0},
                      'ions': {'k': {'e': -77.0, 'i': 54.4, 'o': 2.5},
                               'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                      'mechs': {'B_Na': {'gnabar': 0.03, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                                'HH2': {'gkbar': 0.304, 'gnabar': 0.02375, 'vtraub': -50.2},
                                'borgka': {'gkabar': 0.1120 * 1.0 },
                                'KDRI': {'gkbar': 0.01547},
                                'pas': {'g': 0.96e-06, 'e': -65.0}},
                      'topol': {'parentSec': 'soma', 'parentX': 1.0, 'childX': 0.0}},
          'soma': {'geom': {'L': 20.0, 'nseg': 3, 'diam': 20.0, 'Ra': 150.0, 'cm': 1.0},
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'B_Na': {'gnabar': 0.0001652, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                             'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 1.0, 'depth': 0.1},
                             'HH2': {'gkbar': 0.0043, 'gnabar': 0.08548, 'vtraub': -50.2},
                             'borgka': {'gkabar': 0.01090 * 1.0 },
                             'KDRI': {'gkbar': 0.0001110},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'pas': {'g': 0.96e-06, 'e': -65.0}},
                   'topol': {}}}
}

PKCRule  = {
 'conds': {},
 'globals': {},
 'secLists': {},
 'secs': {'dend': {'geom': {'L': 400.0, 'nseg': 5, 'diam': 3.0, 'Ra': 150.0, 'cm': 1.0}, 
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 2.0, 'depth': 0.1},
                             'HH2': {'gnabar': 0.0, 'gkbar': 0.144, 'vtraub': -50.2},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'borgka': {'gkabar': 0.0009333},
                             'KDRI': {'gkbar': 0.96e-05},
                             'pas': {'g': 0.96e-06, 'e': -65.0}},
                   'topol': {'parentSec': 'soma', 'parentX': 0.0, 'childX': 0.0}},
          'hillock': {'geom': {'L': 9.0, 'nseg': 3, 'diam': 1.5, 'Ra': 150.0, 'cm': 1.0},
                      'ions': {'k': {'e': -77.0, 'i': 54.4, 'o': 2.5},
                               'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                      'mechs': {'B_Na': {'gnabar': 0.03, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                                'HH2': {'gkbar': 0.304, 'gnabar': 0.02375, 'vtraub': -50.2},
                                'borgka': {'gkabar': 0.1120 * 1.0 },
                                'KDRI': {'gkbar': 0.01547},
                                'pas': {'g': 0.96e-06, 'e': -65.0}},
                      'topol': {'parentSec': 'soma', 'parentX': 1.0, 'childX': 0.0}},
          'soma': {'geom': {'L': 20.0, 'nseg': 3, 'diam': 20.0, 'Ra': 150.0, 'cm': 1.0},
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'B_Na': {'gnabar': 0.0001652, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                             'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 1.0, 'depth': 0.1},
                             'HH2': {'gkbar': 0.0043, 'gnabar': 0.08548, 'vtraub': -50.2},
                             'borgka': {'gkabar': 0.01090 * 1.0 },
                             'KDRI': {'gkbar': 0.0001110},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'pas': {'g': 0.96e-06, 'e': -65.0}},
                   'topol': {}}}
}

SOMRule  = {
 'conds': {},
 'globals': {},
 'secLists': {},
 'secs': {'dend': {'geom': {'L': 400.0, 'nseg': 5, 'diam': 3.0, 'Ra': 150.0, 'cm': 1.0}, 
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 2.0, 'depth': 0.1},
                             'HH2': {'gnabar': 0.0, 'gkbar': 0.144, 'vtraub': -50.2},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'borgka': {'gkabar': 0.0009333},
                             'KDRI': {'gkbar': 0.96e-05},
                             'pas': {'g': 0.96e-06, 'e': -65.0}},
                   'topol': {'parentSec': 'soma', 'parentX': 0.0, 'childX': 0.0}},
          'hillock': {'geom': {'L': 9.0, 'nseg': 3, 'diam': 1.5, 'Ra': 150.0, 'cm': 1.0},
                      'ions': {'k': {'e': -77.0, 'i': 54.4, 'o': 2.5},
                               'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                      'mechs': {'B_Na': {'gnabar': 0.03, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                                'HH2': {'gkbar': 0.304, 'gnabar': 0.02375, 'vtraub': -50.2},
                                'borgka': {'gkabar': 0.1120 * 1.0 },
                                'KDRI': {'gkbar': 0.01547},
                                'pas': {'g': 0.96e-06, 'e': -65.0}},
                      'topol': {'parentSec': 'soma', 'parentX': 1.0, 'childX': 0.0}},
          'soma': {'geom': {'L': 20.0, 'nseg': 3, 'diam': 20.0, 'Ra': 150.0, 'cm': 1.0},
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'B_Na': {'gnabar': 0.0001652, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                             'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 1.0, 'depth': 0.1},
                             'HH2': {'gkbar': 0.0043, 'gnabar': 0.08548, 'vtraub': -50.2},
                             'borgka': {'gkabar': 0.01090 * 1.0 },
                             'KDRI': {'gkbar': 0.0001110},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'pas': {'g': 0.96e-06, 'e': -65.0}},
                   'topol': {}}}
}

CRRule  = {
 'conds': {},
 'globals': {},
 'secLists': {},
 'secs': {'dend': {'geom': {'L': 400.0, 'nseg': 5, 'diam': 3.0, 'Ra': 150.0, 'cm': 1.0}, 
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 2.0, 'depth': 0.1},
                             'HH2': {'gnabar': 0.0, 'gkbar': 0.144, 'vtraub': -50.2},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'borgka': {'gkabar': 0.0009333},
                             'KDRI': {'gkbar': 0.96e-05},
                             'pas': {'g': 0.96e-06, 'e': -65.0}},
                   'topol': {'parentSec': 'soma', 'parentX': 0.0, 'childX': 0.0}},
          'hillock': {'geom': {'L': 9.0, 'nseg': 3, 'diam': 1.5, 'Ra': 150.0, 'cm': 1.0},
                      'ions': {'k': {'e': -77.0, 'i': 54.4, 'o': 2.5},
                               'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                      'mechs': {'B_Na': {'gnabar': 0.03, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                                'HH2': {'gkbar': 0.304, 'gnabar': 0.02375, 'vtraub': -50.2},
                                'borgka': {'gkabar': 0.1120 * 1.0 },
                                'KDRI': {'gkbar': 0.01547},
                                'pas': {'g': 0.96e-06, 'e': -65.0}},
                      'topol': {'parentSec': 'soma', 'parentX': 1.0, 'childX': 0.0}},
          'soma': {'geom': {'L': 20.0, 'nseg': 3, 'diam': 20.0, 'Ra': 150.0, 'cm': 1.0},
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'B_Na': {'gnabar': 0.0001652, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                             'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 1.0, 'depth': 0.1},
                             'HH2': {'gkbar': 0.0043, 'gnabar': 0.08548, 'vtraub': -50.2},
                             'borgka': {'gkabar': 0.01090 * 1.0 },
                             'KDRI': {'gkbar': 0.0001110},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'pas': {'g': 0.96e-06, 'e': -65.0}},
                   'topol': {}}}
}

EXinitialRule  = {
 'conds': {},
 'globals': {},
 'secLists': {},
 'secs': {'dend': {'geom': {'L': 400.0, 'nseg': 5, 'diam': 3.0, 'Ra': 150.0, 'cm': 1.0}, 
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 2.0, 'depth': 0.1},
                             'HH2': {'gnabar': 0.0, 'gkbar': 0.0, 'vtraub': -50.2},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'borgka': {'gkabar': 0.0001584},
                             'KDRI': {'gkbar': 0.2061},
                             'pas': {'g': 4.2e-05, 'e': -65.0}},
                   'topol': {'parentSec': 'soma', 'parentX': 0.0, 'childX': 0.0}},
          'hillock': {'geom': {'L': 9.0, 'nseg': 3, 'diam': 1.5, 'Ra': 150.0, 'cm': 1.0},
                      'ions': {'k': {'e': -77.0, 'i': 54.4, 'o': 2.5},
                               'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                      'mechs': {'B_Na': {'gnabar': 5.147, 'alpha_shift': 6.713, 'beta_shift': 9.906},
                                'HH2': {'gkbar': 0.0, 'gnabar': 0.0, 'vtraub': -50.2},
                                'borgka': {'gkabar': 0.0005},
                                'KDRI': {'gkbar': 0.2171},
                                'pas': {'g': 4.2e-05, 'e': -65.0}},
                      'topol': {'parentSec': 'soma', 'parentX': 1.0, 'childX': 0.0}},
          'soma': {'geom': {'L': 20.0, 'nseg': 3, 'diam': 20.0, 'Ra': 150.0, 'cm': 1.0},
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'B_Na': {'gnabar': 0.3066, 'alpha_shift': 6.713, 'beta_shift': 9.906},
                             'CaIntraCellDyn': {'cai_inf': 5e-05, 'cai_tau': 1.0, 'depth': 0.1},
                             'HH2': {'gkbar': 0.0, 'gnabar': 0.0, 'vtraub': -50.2},
                             'borgka': {'gkabar': 0.04957},
                             'KDRI': {'gkbar': 1.06e-05},
                             'iKCa': {'gbar': 0.002, 'gk': 0.0},
                             'pas': {'g': 4.2e-05, 'e': -65.0}},
                   'topol': {}}}
}

INcellRule  = {# was termed SG cell in prior model
 'conds': {},
 'globals': {},
 'secLists': {},
 'secs': {'dend': {'geom': {'L': 1371.0, 'nseg': 50, 'diam': 1.4, 'Ra': 80.0, 'cm': 1.0},
                   'ions': {'k': {'e': -84.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 60.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'B_DR': {},
                             'KDR': {'gkbar': 0.0},
                             'KDRI': {'gkbar': 0.034},
                             'SS': {'gnabar': 0.0},
                             'pas': {'g': 1.1e-05, 'e': -70.0}},
                   'topol': {'parentSec': 'soma', 'parentX': 0.0, 'childX': 0.0}},
          'hillock': {'geom': {'L': 30.0,
                               'Ra': 80.0,
                               'cm': 1.0,
                               'diam': 0.742,
                               'nseg': 30},
                      'ions': {'k': {'e': -84.0, 'i': 54.4, 'o': 2.5},
                               'na': {'e': 60.0, 'i': 10.0, 'o': 140.0}},
                      'mechs': {'B_A': {},
                                'B_DR': {},
                                'B_Na': {'gnabar': 3.45, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                                'KDR': {'gkbar': 0.0},
                                'KDRI': {'gkbar': 0.076},
                                'pas': {'g': 1.1e-05, 'e': -70.0}},
                      'topol': {'parentSec': 'soma', 'parentX': 1.0, 'childX': 0.0}},
          'soma': {'geom': {'L': 10.0, 'nseg': 10, 'diam': 10.0, 'Ra': 80.0, 'cm': 1.0},
                   'ions': {'k': {'e': -84.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 60.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'B_A': {},
                             'B_DR': {},
                             'B_Na': {'gnabar': 0.008, 'alpha_shift': 0.0, 'beta_shift': 0.0},
                             'KDR': {'gkbar': 0.0},
                             'KDRI': {'gkbar': 0.0043},
                             'pas': {'g': 1.1e-05, 'e': -70.0}},
                   'topol': {}}}
}

PROcellRule = {
 'conds': {},
 'globals': {},
 'secLists': {},
 'secs': {'dend': {'geom': {'L': 350.0, 'nseg': 5, 'diam': 2.5, 'Ra': 150.0, 'cm': 1.0},
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'can': {'e': 0.0, 'i': 1.0, 'o': 1.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'CaIntraCellDyn': {'cai_inf': 5e-05,
                                                'cai_tau': 2.0,
                                                'depth': 0.1},
                             'HH2': {'gnabar': 0.0, 'gkbar': 0.036, 'vtraub': -55.0},
                             'iCaAN': {'gbar': 9.099999999999999e-05},
                             'iCaL': {'pcabar': 3e-05},
                             'iKCa': {'gbar': 0.001, 'gk': 0.0},
                             'pas': {'g': 4.2e-05, 'e': -65.0}},
                   'topol': {'parentSec': 'soma', 'parentX': 0.0, 'childX': 0.0}},
          'hillock': {'geom': {'L': 9.0, 'nseg': 3, 'diam': 1.5, 'Ra': 150.0, 'cm': 1.0},
                      'ions': {'k': {'e': -77.0, 'i': 54.4, 'o': 2.5},
                               'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                      'mechs': {'B_A': {},
                                'HH2': {'gkbar': 0.076,
                                        'gnabar': 3.45,
                                        'vtraub': -55.0},
                                'pas': {'g': 4.2e-05, 'e': -65.0}},
                      'topol': {'parentSec': 'soma', 'parentX': 1.0, 'childX': 0.0}},
          'soma': {'geom': {'L': 20.0, 'nseg': 3, 'diam': 20.0, 'Ra': 150.0, 'cm': 1.0},
                   'ions': {'ca': {'e': 132.4579341637009, 'i': 5e-05, 'o': 2.0},
                            'can': {'e': 0.0, 'i': 1.0, 'o': 1.0},
                            'k': {'e': -70.0, 'i': 54.4, 'o': 2.5},
                            'na': {'e': 50.0, 'i': 10.0, 'o': 140.0}},
                   'mechs': {'CaIntraCellDyn': {'cai_inf': 5e-05,
                                                'cai_tau': 1.0,
                                                'depth': 0.1},
                             'HH2': {'gkbar': 0.001075,
                                     'gnabar': 0.0,
                                     'vtraub': -55.0},
                             'iCaAN': {'gbar': 0.0},
                             'iCaL': {'pcabar': 0.0001},
                             'iKCa': {'gbar': 0.0001, 'gk': 0.0},
                             'iNaP': {'gamma': 0.5,
                                      'gnabar': 0.0001,
                                      'vsh': -5.0,
                                      'vsm': -2.0,
                                      'vtraub': -55.0},
                             'pas': {'g': 4.2e-05, 'e': -65.0}},
                   'topol': {}}}
}


def createIN():
    cellRule = {
        'secs': {
                 'soma'   : {'L': 10.0, 'diam': 10.0, 'nseg': 1 , 'Ra': 150},
                 'dend'   : {'L': 1371, 'diam': 1.4 , 'nseg': 77, 'Ra': 150},
                 'hillock': {'L': 30  , 'diam': 1.5 , 'nseg': 3 , 'Ra': 150},
        },# using dlambda 0.1, freq < 100
        'ions': {'k': -84.0, 'na': 60, 'ca': 132.5},
        'mechs': {'pas': {'g': 1.1e-05, 'e': -70}},
        'cons': (
                 ('dend', 'soma'),
                 ('soma', 'hillock')
                )}
    IN = genrn(**cellRule)
    IN/'soma'<{'B_Na': {'gnabar': 0.008},
               'B_A': {}, 'B_DR': {}, 'KDR': {},
               'KDRI': {'gkbar': 0.0043}}
    IN/'hillock'<{'B_Na': {'gnabar': 3.45},
                  'B_A': {}, 'B_DR': {}, 'KDR': {},
                  'KDRI': {'gkbar': 0.076}}
    IN/'dend'<{'SS': {'gnabar':0},
               'B_DR': {},
               'KDR': {},
               'KDRI': {'gkbar':0.034}}
    IN.init_nernsts()
    return IN

def createEX():
    cellRule = {
        'secs': {
                 'dend'   : {'L': 400 , 'diam': 3.0 , 'nseg': 15, 'Ra': 150},
                 'soma'   : {'L': 20.0, 'diam': 20.0, 'nseg': 1 , 'Ra': 150},
                 'hillock': {'L': 9.0 , 'diam': 1.5 , 'nseg': 1 , 'Ra': 150},
        },# using dlambda 0.1, freq < 100
        'ions': {'k': -70.0, 'na': 53.0, 'ca': 132.5},
        'mechs': {'pas': {'g': 4.2e-05, 'e': -65}},
        'cons': (
                 ('dend', 'soma'),
                 ('soma', 'hillock')
                )}
    EX = genrn(**cellRule)
    EX/'dend'<{'HH2': {'gnabar': 0, 'gkbar': 0.036},
               'CaIntraCellDyn': {'depth': 0.1, 'cai_tau': 2.0, 'cai_inf': 50e-6},
               'iKCa': {'gbar': 0.002}}
    EX/'soma'<{'HH2': {'gnabar': 0, 'gkbar': 0.001075, 'vtraub': -55},
               'CaIntraCellDyn': {'depth': 0.1, 'cai_tau': 1.0, 'cai_inf': 50e-6},
               'iKCa': {'gbar': 0.002}}
    EX/'hillock'<{'HH2': {'gnabar': 3.45, 'gkbar': 0.076, 'vtraub': -55}}
    # axon only has one mechanism besides pas, with 0 ion conductance
    EX.init_nernsts()
    return EX

def createPRO():
    cellRule = {
        'secs': {
                 'soma'   : {'L': 20.0, 'diam': 20.0, 'nseg': 1 , 'Ra': 150},
                 'dend'   : {'L': 350 , 'diam': 2.5 , 'nseg': 15, 'Ra': 150},
                 'hillock': {'L': 9.0 , 'diam': 1.5 , 'nseg': 1 , 'Ra': 150},
        },
        'ions': {'k': -70.0, 'na': 53.0, 'ca': 132.5},
        'mechs': {'pas': {'g': 4.2e-05, 'e': -65}},
        'cons': (
                 ('dend', 'soma'),
                 ('soma', 'hillock')
                )}
    PRO = genrn(**cellRule)
    PRO/'soma'<{'HH2': {'gnabar': 0, 'gkbar': 0.001075, 'vtraub': -55},
                'CaIntraCellDyn': {'depth': 0.1, 'cai_tau': 1.0, 'cai_inf': 50e-6},
                'iCaL': {'pcabar': 0.001},
                'iKCa': {'gbar': 0.0001},
                'iNaP': {'gnabar': 0.0001}}
    PRO/'dend'<{'HH2': {'gnabar': 0, 'gkbar': 0.036},
                'CaIntraCellDyn': {'depth': 0.1, 'cai_tau': 2.0, 'cai_inf':50e-6},
                'iCaL': {'pcabar': 3e-5},
                'iKCa': {'gbar': 0.001}}
    PRO/'hillock'<{'HH2': {'gnabar': 3.45, 'gkbar': 0.076, 'vtraub': -55}}
    return PRO

if __name__=='__main__':
    inc = createIN()
    exc = createEX()
    proc= createPRO()

    print("IN cell:\n%s"  %(inc) )
    print("EX cell:\n%s"  %(exc) )
    print("PRO cell:\n%s" %(proc))
    pass