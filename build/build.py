#!/usr/bin/env python
import sys
import os
import shutil
import re
from base import system_info
from base import run_command

class BuildError(Exception):
    def __init__(self, value):
        self.value_ = value
    def __str__(self):
        return self.value_

def print_usage():
    print("Usage:\n"
        "[required] argv[1] cmake_root_path\n"
        "[optional] argv[2] branding_file_path\n"
        "[optional] argv[3] platform\n"
        "[optional] argv[4] architecture\n"
        "[optional] argv[5] packages for example(\"DEB RPM\")\n")


class CommonPolicy(run_command.Policy):
    def __init__(self, cb):
        run_command.Policy.__init__(self, cb)

class CmakePolicy(run_command.Policy):
    def __init__(self, cb):
        run_command.Policy.__init__(self, cb)

    def process(self, message):
        self.progress_ += 1.0
        super(CmakePolicy, self).process(message)

    def update_progress_message(self, progress, message):
        super(CmakePolicy, self).update_progress_message(progress, message)

class NinjaPolicy(run_command.Policy):
    def __init__(self, cb):
        run_command.Policy.__init__(self, cb)

    def process(self, message):
        if message.type() != run_command.MessageType.MESSAGE:
            super(NinjaPolicy, self).process(message)
            return

        cur,total = self.parse_message_to_get_range(message.message())
        if not cur and not total:
            return

        self.progress_ = cur / total * 100.0
        super(NinjaPolicy, self).process(message)

    def update_progress_message(self, progress, message):
        super(NinjaPolicy, self).update_progress_message(progress, message)

    def parse_message_to_get_range(self, message):
        if not message:
            return None, None

        res = re.search(r'\A\[(\d+)/(\d+)\]', message)
        if res != None:
            return float(res.group(1)), float(res.group(2))

        return None, None

def read_file_line_by_line(file):
    if not os.path.exists(file):
        raise BuildError('file path: %s not exists' % file)

    file_array = []
    with open(file, "r") as ins:
        for line in ins:
            file_array.append(line.strip())

    return file_array

class ProgressSaverBase(object):
    def __init__(self):
        self.progress_min_ = 0.0
        self.progress_max_ = 0.0

    def update_progress_message_range(self, progress_min, progress_max, message):
        self.progress_min_ = progress_min
        self.progress_max_ = progress_max
        print '{0:.2f}% {1}'.format(progress_min, message)

    def on_update_progress_message(self, progress, message):
        if message.type() == run_command.MessageType.STATUS:
            return

        diff = self.progress_max_ - self.progress_min_
        perc = self.progress_min_ + diff * (progress / 100.0)
        print '{0:.2f}% {1}'.format(perc, message.message())

class BuildRequest(object):
    def __init__(self, platform, arch_bit):
        platform_or_none = system_info.get_supported_platform_by_name(platform)

        if platform_or_none == None:
            raise BuildError('invalid platform')

        arch = platform_or_none.architecture_by_bit(arch_bit)
        if arch == None:
            raise BuildError('invalid arch')

        self.platform_ = system_info.Platform(platform_or_none.name(), arch, platform_or_none.package_types())
        print("Build request for platform: {0}, arch: {1} created".format(platform, arch.name()))

    def platform(self):
        return self.platform_

    def build(self, cmake_project_root_path, branding_options, dir_path, package_types, saver):
        cmake_project_root_abs_path = os.path.abspath(cmake_project_root_path)
        if not os.path.exists(cmake_project_root_abs_path):
            raise BuildError('invalid cmake_project_root_path: %s' % cmake_project_root_path)

        if not package_types:
            package_types = self.platform_.package_types()

        abs_dir_path = os.path.abspath(dir_path)
        if os.path.exists(abs_dir_path):
            shutil.rmtree(abs_dir_path)

        saver.update_progress_message_range(0.0, 9.0, "Start building project branding_options:\n{0}".format("\n".join(branding_options)))

        pwd = os.getcwd()
        os.mkdir(abs_dir_path)
        os.chdir(abs_dir_path)

        # project static options
        arch = self.platform_.arch()
        arch_args = '-DOS_ARCH={0}'.format(arch.bit)
        log_to_file_args = '-DLOG_TO_FILE=ON'
        openssl_args = '-DOPENSSL_USE_STATIC=ON'
        cmake_line = ['cmake', cmake_project_root_abs_path, '-GNinja', '-DCMAKE_BUILD_TYPE=RELEASE', arch_args, log_to_file_args, openssl_args]

        if branding_options:
            cmake_line.extend(branding_options)

        saver.update_progress_message_range(10.0, 19.0, 'Generate project build')

        def store(cb):
            def closure(progress, message):
                return cb(progress, message)
            return closure

        store = store(saver.on_update_progress_message)

        try:
            cmake_policy = CmakePolicy(store)
            run_command.run_command_cb(cmake_line, cmake_policy)
        except Exception as ex:
            os.chdir(pwd)
            raise ex

        make_install = ['ninja', 'install']
        saver.update_progress_message_range(20.0, 79.0, 'Build project')
        try:
            ninja_policy = NinjaPolicy(store)
            run_command.run_command_cb(make_install, ninja_policy)
        except Exception as ex:
            os.chdir(pwd)
            raise ex

        saver.update_progress_message_range(80.0, 84.0, 'Trying to get package file name')
        in_file = open('CPackConfig.cmake', 'r')
        for line in in_file.readlines():
            res = re.search(r'SET\(CPACK_PACKAGE_FILE_NAME "(.+)"\)', line)
            if res != None:
                filename = res.group(1)
                break
        in_file.close()

        saver.update_progress_message_range(85.0, 99.0, 'Start build package')
        file_names = []
        if self.platform_.name() == 'android':
            make_apk_release = ['ninja', 'apk_release']
            try:
                common_policy = CommonPolicy(store)
                run_command.run_command_cb(make_apk_release, common_policy)
            except Exception as ex:
                os.chdir(pwd)
                raise ex
            make_apk_signed = ['ninja', 'apk_signed']
            try:
                common_policy = CommonPolicy(store)
                run_command.run_command_cb(make_apk_signed, common_policy)
            except Exception as ex:
                os.chdir(pwd)
                raise ex
            make_apk_signed_aligned = ['ninja', 'apk_signed_aligned']
            try:
                common_policy = CommonPolicy(store)
                run_command.run_command_cb(make_apk_signed_aligned, common_policy)
            except Exception as ex:
                os.chdir(pwd)
                raise ex

            file_names.append(os.path.join(abs_dir_path, filename + '.' + system_info.get_extension_by_package('APK')))
        else:
            for generator in package_types:
                make_cpack = ['cpack', '-G', generator]
                try:
                    common_policy = CommonPolicy(store)
                    run_command.run_command_cb(make_cpack, common_policy)
                    file_names.append(os.path.join(abs_dir_path, filename + '.' + system_info.get_extension_by_package(generator)))
                except Exception as ex:
                    os.chdir(pwd)
                    raise ex

        os.chdir(pwd)

        saver.update_progress_message_range(100.0, 100.0, "Building finished successfully file_names: {0}".format(file_names))
        return file_names

if __name__ == "__main__":
    argc = len(sys.argv)

    if argc > 1:
        cmake_root = sys.argv[1]
    else:
        print_usage()
        sys.exit(1)

    if argc > 2:
        branding_file_path = sys.argv[2]
    else:
        branding_file_path = '/dev/null'
        
    if argc > 3:
        platform_str = sys.argv[3]
    else:
        platform_str = system_info.get_os()

    if argc > 4:
        arch_bit_str = sys.argv[4]
    else:
        arch_bit_str = system_info.get_arch_bit()

    if argc > 5:
        packages = sys.argv[5].split()
    else:
        packages = []
        
    request = BuildRequest(platform_str, int(arch_bit_str))
    if branding_file_path != '/dev/null':
        abs_branding_file = os.path.abspath(branding_file_path)
        branding_options = read_file_line_by_line(abs_branding_file)
    else:
        branding_options = []


    saver = ProgressSaverBase()
    request.build(cmake_root, branding_options, 'build_' + platform_str, packages, saver)