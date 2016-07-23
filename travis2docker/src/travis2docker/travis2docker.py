import collections
import os
import re
import stat
from tempfile import gettempdir

import yaml

RE_ENV_STR = r"(?P<var>[\w]*)[  ]*[\=][  ]*[\"\']{0,1}" + \
             r"(?P<value>[\w\.\-\_/\$\{\}\:,\(\)\#\* ]*)[\"\']{0,1}"
RE_EXPORT_STR = r"^(?P<export>export|EXPORT)(  )+" + RE_ENV_STR


class Travis2Docker(object):

    re_export = re.compile(RE_EXPORT_STR, re.M)
    curr_work_path = None
    curr_exports = []

    @staticmethod
    def load_yml(yml_path):
        yml_path = os.path.expandvars(os.path.expanduser(yml_path))
        if os.path.isdir(yml_path):
            yml_path = os.path.join(yml_path, '.travis.yml')
        if not os.path.isfile(yml_path):
            return
        with open(yml_path, "r") as f_yml:
            return yaml.load(f_yml)

    def __init__(self, yml_path, image, work_path=None, dockerfile=None):
        if dockerfile is None:
            dockerfile = 'Dockerfile'
        self.image = image
        self._sections = collections.OrderedDict()
        self._sections['env'] = 'env'
        self._sections['install'] = 'run'
        self._sections['script'] = 'entrypoint'
        self._sections['after_success'] = 'entrypoint'
        self.yml = self.load_yml(yml_path)
        if work_path is None:
            base_name = os.path.splitext(os.path.basename(__file__))[0]
            self.work_path = os.path.join(gettempdir(), base_name)
            if not os.path.isdir(self.work_path):
                os.mkdir(self.work_path)
        else:
            self.work_path = os.path.expandvars(os.path.expanduser(root_path))
        self.dockerfile = dockerfile

    def _compute(self, section):
        section_type = self._sections.get(section)
        if not section_type:
            return None
        section_data = self.yml.get(section, "")
        if isinstance(section_data, basestring):
            section_data = [section_data]
        job_method = getattr(self, '_compute_' + section_type)
        return job_method(section_data, section)

    def _compute_env(self, data, section):
        if isinstance(data, list):
            # old version without matrix
            data = {'matrix': data}
        env_globals = ""
        for env_global in data.get('global', []):
            if isinstance(env_global, dict):
                # we can't use the secure encrypted variables
                continue
            env_globals += " " + env_global
        env_globals = env_globals.strip()
        for env_matrix in data.get('matrix', []):
            yield "ENV " + (env_globals + " " + env_matrix).strip()

    def _compute_run(self, data, section):
        args = self._make_script(data, section)
        args['cmds'].append('RUN %(dst)s' % args )
        return '\n'.join(args['cmds'])

    @staticmethod
    def chmod_execution(file_path):
        st = os.stat(file_path)
        os.chmod(file_path, st.st_mode | stat.S_IEXEC)

    def _make_script(self, data, section):
        file_path = os.path.join(self.curr_work_path, section)
        with open(file_path, "w") as f_section:
            for var, value in self.curr_exports:
                f_section.write('\nEXPORT %s=%s' % (var, value))
            for line in data:
                if 'export' in line.lower():
                    import pdb;pdb.set_trace()
                self.curr_exports.extend([
                    (var, value)
                    for _, _, var, value in self.re_export.findall(line)])
                f_section.write('\n' + line)
        args = {
            'src': os.path.relpath(file_path, self.curr_work_path),
            'dst': "/" + section,
        }
        self.chmod_execution(file_path)
        args['cmds'] = ["COPY %(src)s %(dst)s" % args]
        return args

    def reset(self):
        self.curr_work_path = None
        self.curr_exports = []

    def _compute_entrypoint(self, data, section):
        args = self._make_script(data, section)
        return '\n'.join(args['cmds'])

    def compute_dockerfile(self):
        sections = self._sections.copy()
        sections.pop('env')
        for count, env in enumerate(self._compute('env'), 1):
            self.curr_work_path = os.path.join(self.work_path, str(count))
            if not os.path.isdir(self.curr_work_path):
                os.mkdir(self.curr_work_path)
            curr_dockerfile = \
                os.path.join(self.curr_work_path, self.dockerfile)
            entryp_path = os.path.join(self.curr_work_path, "entrypoint.sh")
            entryp_relpath = os.path.relpath(entryp_path, self.curr_work_path)
            with open(curr_dockerfile, "w") as f_dockerfile, \
                    open(entryp_path, "w") as f_entrypoint:
                f_dockerfile.write("FROM " + self.image + "\n")
                f_dockerfile.write(env + "\n")
                f_dockerfile.write("COPY " + entryp_relpath + " /entrypoint.sh\n")
                for section, type_section in sections.items():
                    result = self._compute(section)
                    if not result:
                        continue
                    f_dockerfile.write(result + "\n")
                    if type_section == 'entrypoint':
                        f_entrypoint.write("/" + section + '\n')
                f_dockerfile.write("ENTRYPOINT /entrypoint.sh\n")
            self.chmod_execution(entryp_path)
        self.reset()


if __name__ == '__main__':
    yml_path = "/Users/moylop260/odoo/yoytec/.travis.yml"
    yml_path = "~/odoo/l10n-argentina"
    t2d = Travis2Docker(yml_path, 'vauxoo/odoo-80-image-shippable-auto')
    t2d.compute_dockerfile()
    print t2d.work_path
    # print open(t2d.dockerfile).read()
