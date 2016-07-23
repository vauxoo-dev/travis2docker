import collections
import os
import stat
from tempfile import gettempdir

import yaml


class Travis2Docker(object):

    data = None

    @staticmethod
    def load_yml(yml_path):
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
        self.dockerfile = os.path.join(self.work_path, dockerfile)

    def _compute(self, section):
        section_type = self._sections.get(section)
        if not section_type:
            return None
        section_data = self.yml.get(section, "")
        if isinstance(section_data, basestring):
            section_data = [section_data]
        job_method = getattr(self, '_compute_' + section_type)
        self.data = section_data
        return job_method(section_data, section)

    def _compute_env(self, data, section):
        env_globals = ""
        for env_global in data.get('global', []):
            if isinstance(env_global, dict):
                # we can't use the secure encrypted variables
                continue
            env_globals += " " + env_global
        return "ENV " + env_globals.strip() if env_globals else ""

    def _compute_run(self, data, section):
        args = self._make_script(data, section)
        args['cmds'].append('RUN %(dst)s' % args )
        return '\n'.join(args['cmds'])

    @staticmethod
    def chmod_execution(file_path):
        st = os.stat(file_path)
        os.chmod(file_path, st.st_mode | stat.S_IEXEC)

    def _make_script(self, data, section):
        file_path = os.path.join(self.work_path, section)
        with open(file_path, "w") as f_section:
            f_section.write('\n'.join(data or []))
        args = {
            'src': os.path.relpath(file_path, self.work_path),
            'dst': "/" + section,
        }
        self.chmod_execution(file_path)
        args['cmds'] = ["COPY %(src)s %(dst)s" % args]
        return args

    def _compute_entrypoint(self, data, section):
        # TODO: How to process the export of run here,
        #       I don't know if a source works
        args = self._make_script(data, section)
        return '\n'.join(args['cmds'])

    def compute_dockerfile(self):
        entryp_path = os.path.join(self.work_path, "entrypoint.sh")
        entryp_relpath = os.path.relpath(entryp_path, self.work_path)
        with open(self.dockerfile, "w") as f_dockerfile, \
                open(entryp_path, "w") as f_entrypoint:
            f_dockerfile.write("FROM " + self.image + "\n")
            f_dockerfile.write("COPY " + entryp_relpath + " /entrypoint.sh\n")
            for section, type_section in self._sections.items():
                result = self._compute(section)
                if not result:
                    continue
                f_dockerfile.write(result + "\n")
                print type_section, section
                if type_section == 'entrypoint':
                    f_entrypoint.write("/" + section + '\n')
            f_dockerfile.write("ENTRYPOINT /entrypoint.sh\n")
        self.chmod_execution(entryp_path)


if __name__ == '__main__':
    yml_path = "/Users/moylop260/odoo/yoytec/.travis.yml"
    # yml = Travis2Docker.load_travis_file(yml_path)
    t2d = Travis2Docker(yml_path, 'vauxoo/odoo-80-image-shippable-auto')
    t2d.compute_dockerfile()
    print t2d.work_path
    print open(t2d.dockerfile).read()
