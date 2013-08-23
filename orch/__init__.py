#!/usr/bin/env python
# encoding: utf-8

import os
from glob import glob
from . import pkgconf
from . import features
from . import envmunge

# NOT from the waf book.  The waf book example for depends_on doesn't work
from waflib import TaskGen
@TaskGen.feature('*') 
@TaskGen.before_method('process_rule')
def post_the_other(self):
    deps = getattr(self, 'depends_on', []) 
    for name in self.to_list(deps):
        print ('DEPENDS_ON: %s %s' % ( self.name, name ))
        other = self.bld.get_tgen_by_name(name) 
        other.post()
        for ot in other.tasks:
            print ('OTHER TASK: %s before: %s' % (ot, ot.before))
            ot.before.append(self.name)


# waf entries
def options(opt):
    opt.add_option('--orch-config', action = 'store', default = 'orch.cfg',
                   help='Give an orchestration configuration file.')
    opt.add_option('--orch-start', action = 'store', default = 'start',
                   help='Set the section to start the orchestration')


def bind_functions(ctx):
    from pprint import PrettyPrinter
    pp = PrettyPrinter(indent=2)
    ctx.orch_dump = lambda : pp.pprint({'packages': ctx.env.orch_package_list,
                                        'groups': ctx.env.orch_group_list})
    ctx.orch_pkgdata = lambda name, var=None: \
                       features.get_pkgdata(ctx.env.orch_package_dict, name, var)

# fixme: to make recursion more sensible, most of configure() and
# build() should go in ../wscript.  Otherwise there are problems with
# using a customized wscript which needs to use "orch" as a tool

def configure(cfg):
    print ('ORCH CONFIG CALLED')

    if not cfg.options.orch_config:
        raise RuntimeError('No Orchestration configuration file given (--orch-config)')
    orch_config = []
    for lst in cfg.options.orch_config.split(','):
        lst = lst.strip()
        orch_config += glob(lst)
    print ('Configuration files: %s' % ', '.join(orch_config))

    extra = dict(cfg.env)
    suite = pkgconf.load(orch_config, start = cfg.options.orch_start, **extra)

    envmunge.decompose(cfg, suite)

    print ('Configure envs: "%s"' % '", "'.join(cfg.all_envs))

    bind_functions(cfg)
    return

def build(bld):
    print ('ORCH BUILD CALLED')

    from waflib.Build import POST_LAZY, POST_BOTH, POST_AT_ONCE
    bld.post_mode = POST_BOTH # don't fuck with this

    bind_functions(bld)

    for grpname in bld.env.orch_group_list:
        print ('Adding group: "%s"' % grpname)
        bld.add_group(grpname)

    print ('Build envs: "%s"' % '", "'.join(bld.all_envs.keys()))

    to_recurse = []
    for pkgname in bld.env.orch_package_list:
        pkgdata = bld.env.orch_package_dict[pkgname]
        other_dir = os.path.join(bld.launch_dir, pkgname, 'wscript')
        if os.path.exists(other_dir):
            to_recurse.append(pkgname)
            continue
        feat = pkgdata.get('features')
        bld(name = '%s_%s' % (pkgname, feat.replace(' ','_')), features = feat, package_name = pkgname)
    if to_recurse:
        bld.recurse(to_recurse)

