import collections
import os
import re
import shutil
import stat
from tempfile import gettempdir

import yaml
import jinja2

RE_ENV_STR = r"(?P<var>[\w]*)[ ]*[\=][ ]*[\"\']{0,1}" + \
             r"(?P<value>[\w\.\-\_/\$\{\}\:,\(\)\#\* ]*)[\"\']{0,1}"
RE_EXPORT_STR = r"^(?P<export>export|EXPORT)( )+" + RE_ENV_STR


# TODO: Add support for optional after_success
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
        return self.jinja_env.get_template('Dockerfile')

    @property
    def new_image(self):
        image_name = self.os_kwargs['repo_owner'] + '-' + \
            self.os_kwargs['repo_project'] + ':' + \
            self.os_kwargs['revision'].replace('/', '_')
        return image_name.lower()

    @property
    def entrypoint_template(self):
        return self.jinja_env.get_template('entrypoint.sh')

    @property
    def build_template(self):
        return self.jinja_env.get_template('10-build.sh')

    @property
    def run_template(self):
        return self.jinja_env.get_template('20-run.sh')

    @staticmethod
    def chmod_execution(file_path):
        st = os.stat(file_path)
        os.chmod(file_path, st.st_mode | stat.S_IEXEC)

    def __init__(self, yml_path, image, work_path=None, dockerfile=None,
                 templates_path=None, os_kwargs=None, copy_paths=None,
                 ):
        if os_kwargs is None:
            os_kwargs = {}
        if dockerfile is None:
            dockerfile = 'Dockerfile'
        if templates_path is None:
            templates_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), 'templates')
        self.copy_paths = copy_paths
        self.os_kwargs = os_kwargs
        self.jinja_env = \
            jinja2.Environment(loader=jinja2.FileSystemLoader(templates_path))
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
            self.work_path = os.path.expandvars(os.path.expanduser(work_path))
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
            'entrypoints': [dest] if add_entrypoint else [],
            'runs': [dest] if add_run else [],
        }
        self.chmod_execution(file_path)
        return args

    def reset(self):
        self.curr_work_path = None
        self.curr_exports = []

    def compute_dockerfile(self, skip_after_success=False):
        for count, env in enumerate(self._compute('env') or [], 1):
            self.curr_work_path = os.path.join(self.work_path, str(count))
            if not os.path.isdir(self.curr_work_path):
                os.mkdir(self.curr_work_path)
            curr_dockerfile = \
                os.path.join(self.curr_work_path, self.dockerfile)
            entryp_path = os.path.join(self.curr_work_path, "entrypoint.sh")
            build_path = os.path.join(self.curr_work_path, "10-build.sh")
            run_path = os.path.join(self.curr_work_path, "20-run.sh")
            entryp_relpath = os.path.relpath(entryp_path, self.curr_work_path)
            copies = []
            for copy_path, dest in self.copy_paths:
                copies.append((self.copy_path(copy_path), dest))
            kwargs = {'runs': [], 'copies': copies, 'entrypoints': [],
                      'entrypoint_path': entryp_relpath,
                      }
            with open(curr_dockerfile, "w") as f_dockerfile, \
                    open(entryp_path, "w") as f_entrypoint, \
                    open(run_path, "w") as f_run, \
                    open(build_path, "w") as f_build:
                kwargs['image'] = self.image
                kwargs['env'] = env
                for section, type_section in self._sections.items():
                    if section == 'env':
                        continue
                    if skip_after_success and section == 'after_success':
                        continue
                    result = self._compute(section)
                    if not result:
                        continue
                    keys_to_extend = ['copies', 'runs', 'entrypoints'] \
                        if isinstance(result, dict) else []
                    for key_to_extend in keys_to_extend:
                        kwargs[key_to_extend].extend(result[key_to_extend])
                kwargs.update(self.os_kwargs)
                dockerfile_content = \
                    self.dockerfile_template.render(kwargs).strip('\n ')
                f_dockerfile.write(dockerfile_content)
                entrypoint_content = \
                    self.entrypoint_template.render(kwargs).strip('\n ')
                f_entrypoint.write(entrypoint_content)
                new_image = self.new_image + '_' + str(count)
                build_content = \
                    self.build_template.render(
                        image=new_image,
                        dirname_dockerfile=self.curr_work_path).strip('\n ')
                f_build.write(build_content)
                run_content = \
                    self.run_template.render(image=new_image).\
                    strip('\n ')
                f_run.write(run_content)
            self.chmod_execution(run_path)
            self.chmod_execution(build_path)
            self.chmod_execution(entryp_path)
        self.reset()

    def copy_path(self, path):
        """
        :param paths list: List of paths to copy
        """
        src = os.path.expandvars(os.path.expanduser(path))
        basename = os.path.basename(src)
        dest_path = os.path.expandvars(os.path.expanduser(
            os.path.join(self.curr_work_path, basename)))
        if os.path.isdir(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(src, dest_path)
        return os.path.relpath(dest_path, self.curr_work_path)


if __name__ == '__main__':
    yml_path = "/Users/moylop260/odoo/yoytec/.travis.yml"
    yml_path = "~/odoo/l10n-argentina"
    yml_path = "~/odoo/yoytec"
    image = 'vauxoo/odoo-80-image-shippable-auto'
    t2d = Travis2Docker(
        yml_path, image, os_kwargs={
            'user': 'shippable',
            'repo_owner': 'Vauxoo',
            'repo_project': 'yoytec',
            'add_self_rsa_pub': True,
            'remotes': ['Vauxoo', 'Vauxoo-dev'],
            'revision': 'pull/2',
            'git_email': 'moylop@vx.com',
            'git_user': 'moy6',
        },
        copy_paths=[("$HOME/.ssh", "$HOME/.ssh")]
    )
    t2d.compute_dockerfile(skip_after_success=True)
    print t2d.work_path
