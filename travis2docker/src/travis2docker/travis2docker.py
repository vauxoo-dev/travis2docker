import collections
import os
import re
import stat
from tempfile import gettempdir

import yaml
import jinja2

RE_ENV_STR = r"(?P<var>[\w]*)[ ]*[\=][ ]*[\"\']{0,1}" + \
             r"(?P<value>[\w\.\-\_/\$\{\}\:,\(\)\#\* ]*)[\"\']{0,1}"
RE_EXPORT_STR = r"^(?P<export>export|EXPORT)( )+" + RE_ENV_STR


# TODO: Add .ssh keys
# TODO: Add global environment variables of travis (TRAVIS_BUILD_DIR)
# TODO: Clone repository
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

    @property
    def dockerfile_template(self):
        template_dir, template_name = os.path.split(self.template_path)
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
        return env.get_template(template_name)

    @staticmethod
    def chmod_execution(file_path):
        st = os.stat(file_path)
        os.chmod(file_path, st.st_mode | stat.S_IEXEC)

    def __init__(self, yml_path, image, work_path=None, dockerfile=None,
                 template_path=None):
        if dockerfile is None:
            dockerfile = 'Dockerfile'
        if template_path is None:
            template_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'templates', 'Dockerfile')
        self.template_path = template_path
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
            yield (env_globals + " " + env_matrix).strip()

    def _compute_run(self, data, section):
        args = self._make_script(data, section, add_run=True)
        return args

    def _compute_entrypoint(self, data, section):
        args = self._make_script(data, section, add_entrypoint=True)
        return args

    def _make_script(self, data, section, add_entrypoint=False, add_run=False):
        file_path = os.path.join(self.curr_work_path, section)
        with open(file_path, "w") as f_section:
            for var, value in self.curr_exports:
                f_section.write('\nexport %s=%s' % (var, value))
            for line in data:
                self.curr_exports.extend([
                    (var, value)
                    for _, _, var, value in self.re_export.findall(line)])
                f_section.write('\n' + line)
        src = "./" + os.path.relpath(file_path, self.curr_work_path)
        dest = "/" + section
        args = {
            'copies': [(src, dest)],
            'entrypoint': [dest] if add_entrypoint else [],
            'runs': [dest] if add_run else [],
        }
        self.chmod_execution(file_path)
        return args

    def reset(self):
        self.curr_work_path = None
        self.curr_exports = []

    def compute_dockerfile(self):
        for count, env in enumerate(self._compute('env') or [], 1):
            kwargs = {'runs': [], 'copies': []}
            self.curr_work_path = os.path.join(self.work_path, str(count))
            if not os.path.isdir(self.curr_work_path):
                os.mkdir(self.curr_work_path)
            curr_dockerfile = \
                os.path.join(self.curr_work_path, self.dockerfile)
            entryp_path = os.path.join(self.curr_work_path, "entrypoint.sh")
            entryp_relpath = os.path.relpath(entryp_path, self.curr_work_path)
            with open(curr_dockerfile, "w") as f_dockerfile, \
                    open(entryp_path, "w") as f_entrypoint:
                kwargs['image'] = self.image
                kwargs['entrypoint'] = entryp_relpath
                kwargs['env'] = env
                for section, type_section in self._sections.items():
                    if section == 'env':
                        continue
                    result = self._compute(section)
                    if not result:
                        continue
                    if isinstance(result, dict):
                        kwargs['copies'].extend(result['copies'])
                        kwargs['runs'].extend(result['runs'])
                        for entrypoint in result['entrypoint']:
                            f_entrypoint.write(entrypoint)
                dockerfile_content = \
                    self.dockerfile_template.render(kwargs).strip('\n ')
                f_dockerfile.write(dockerfile_content)
            self.chmod_execution(entryp_path)
        self.reset()


if __name__ == '__main__':
    yml_path = "/Users/moylop260/odoo/yoytec/.travis.yml"
    yml_path = "~/odoo/l10n-argentina"
    yml_path = "~/odoo/yoytec"
    t2d = Travis2Docker(yml_path, 'vauxoo/odoo-80-image-shippable-auto')
    t2d.compute_dockerfile()
    print t2d.work_path
    # print t2d.dockerfile_template
    # kwargs = {'image': 'vauxoo'}
    # dockerfile_content = t2d.dockerfile_template.render(kwargs)
    # print dockerfile_content
