import os, sys, glob, urllib.parse

from doit.action import CmdAction

DOIT_CONFIG = {
  "default_tasks": [],
}

CHART_ROOT_DIR = ".helm/charts"
CHART_PACKAGE_DIR = ".packages"

DEFAULT_WERF_VERSION = "1.1 ea"
DEFAULT_WERF_COLOR_MODE = "on"
DEFAULT_WERF_ENVS = ["test", "prod"]
DEFAULT_WERF_GLOBAL_CI_URL = "example.org"


################################################################################
# Tasks
################################################################################


def task_werf_lint_charts():
  """ Lint werf chart(s) """

  def werf_lint_charts(chart_names, envs, werf_version, werf_color_mode, extra_args, extra_env_vars):
    if not chart_names:
      chart_names = get_all_chart_names(CHART_ROOT_DIR)
    if not envs:
      envs = DEFAULT_WERF_ENVS

    commands = []
    commands += action_export_env_vars(extra_env_vars)
    commands += action_prepare_werf(werf_version, werf_color_mode)
    for chart_name in chart_names:
      for env in envs:
        commands += action_werf_lint(env, chart_name, extra_args)
    return " && ".join(commands)

  return {
    "basename": "werf-lint",
    "verbosity": 2,
    "actions": [CmdAction(werf_lint_charts, executable="/bin/bash")],
    "params": get_common_werf_params() + get_common_extra_params() + [
      {
        "name": "chart_names",
        "short": "c",
        "long": "chart-name",
        "type": list,
        "default": [],
        "help": f"Chart name, can be specified multiple times. Default: {get_all_chart_names(CHART_ROOT_DIR)}",
      },
      {
        "name": "envs",
        "long": "env",
        "type": list,
        "default": [],
        "help": f"Werf environment, can be specified multiple times. Default: {DEFAULT_WERF_ENVS}",
      },
    ],
  }


def task_werf_render_charts():
  """ Render werf chart(s) """

  def werf_render_charts(chart_names, envs, werf_version, werf_color_mode, extra_args, extra_env_vars):
    if not chart_names:
      chart_names = get_all_chart_names(CHART_ROOT_DIR)
    if not envs:
      envs = DEFAULT_WERF_ENVS

    commands = []
    commands += action_export_env_vars(extra_env_vars)
    commands += action_prepare_werf(werf_version, werf_color_mode)
    for chart_name in chart_names:
      for env in envs:
        commands += action_werf_render(env, chart_name, extra_args)
    return " && ".join(commands)

  return {
    "basename": "werf-render",
    "verbosity": 2,
    "actions": [CmdAction(werf_render_charts, executable="/bin/bash")],
    "params": get_common_werf_params() + get_common_extra_params() + [
      {
        "name": "chart_names",
        "short": "c",
        "long": "chart-name",
        "type": list,
        "default": [],
        "help": f"Chart name, can be specified multiple times. Default: {get_all_chart_names(CHART_ROOT_DIR)}",
      },
      {
        "name": "envs",
        "long": "env",
        "type": list,
        "default": [],
        "help": f"Werf environment, can be specified multiple times. Default: {DEFAULT_WERF_ENVS}",
      },
    ],
  }


def task_werf_download_chart_dependencies():
  """ Download chart dependencies from requirements.yaml """

  def werf_download_chart_dependencies(chart_names, werf_version, werf_color_mode, extra_args, extra_env_vars):
    if chart_names:
      chart_paths = get_chart_paths(chart_names, CHART_ROOT_DIR)
    else:
      chart_paths = get_all_chart_paths(CHART_ROOT_DIR)

    commands = []
    commands += action_export_env_vars(extra_env_vars)
    commands += action_prepare_werf(werf_version, werf_color_mode)
    commands += action_werf_download_root_chart_dependencies(extra_args)
    for chart_path in chart_paths:
      commands += action_werf_download_nested_chart_dependencies(chart_path, extra_args)
    return " && ".join(commands)

  return {
    "basename": "werf-download-chart-dependencies",
    "verbosity": 2,
    "actions": [CmdAction(werf_download_chart_dependencies, executable="/bin/bash")],
    "params": get_common_werf_params() + get_common_extra_params() + [
      {
        "name": "chart_names",
        "short": "c",
        "long": "chart-name",
        "type": list,
        "default": [],
        "help": f"Chart name, can be specified multiple times. Default: {get_all_chart_names(CHART_ROOT_DIR)}",
      },
    ],
  }


def task_werf_package_charts():
  """ Package werf chart(s) to publish them as artifact """

  def werf_package_charts(chart_names, extra_args, extra_env_vars):
    if chart_names:
      chart_paths = get_chart_paths(chart_names, CHART_ROOT_DIR)
    else:
      chart_paths = get_all_chart_paths(CHART_ROOT_DIR)

    commands = []
    commands += action_export_env_vars(extra_env_vars)
    for chart_path in chart_paths:
      commands += action_werf_package_chart(chart_path, extra_args)
    return " && ".join(commands)

  return {
    "basename": "werf-package-charts",
    "verbosity": 2,
    "actions": [CmdAction(werf_package_charts, executable="/bin/bash")],
    "params": get_common_extra_params() + [
      {
        "name": "chart_names",
        "short": "c",
        "long": "chart-name",
        "type": list,
        "default": [],
        "help": f"Chart name, can be specified multiple times. Default: {get_all_chart_names(CHART_ROOT_DIR)}",
      },
    ],
  }


def task_werf_publish_chart_packages():
  """ Publish packaged werf chart(s) to ChartMuseum """

  def werf_publish_chart_packages(chart_package_filenames, extra_args, extra_env_vars,
                                  chartmuseum_url=None, chartmuseum_basic_auth_user=None,
                                  chartmuseum_basic_auth_pass=None):
    abort_if_param_undefined({"--chartmuseum-url": chartmuseum_url,
                              "--chartmuseum-basic-auth-user": chartmuseum_basic_auth_user,
                              "--chartmuseum-basic-auth-pass": chartmuseum_basic_auth_pass})
    if chart_package_filenames:
      chart_package_paths = get_chart_package_paths(chart_package_names, CHART_PACKAGE_DIR)
    else:
      chart_package_paths = get_all_chart_package_paths(CHART_PACKAGE_DIR)

    commands = []
    commands += action_export_env_vars(extra_env_vars)
    for package_path in chart_package_paths:
      commands += action_werf_publish_chart_package(
        package_path, chartmuseum_url, chartmuseum_basic_auth_user,
        chartmuseum_basic_auth_pass, extra_args
      )
    return " && ".join(commands)

  return {
    "basename": "werf-publish-chart-packages",
    "verbosity": 2,
    "actions": [CmdAction(werf_publish_chart_packages, executable="/bin/bash")],
    "params": get_common_extra_params() + [
      {
        "name": "chart_package_filenames",
        "short": "p",
        "long": "chart-package-filenames",
        "type": list,
        "default": [],
        "help": f"Chart package filename, can be specified multiple times. Default: {get_all_chart_package_paths(CHART_PACKAGE_DIR)}",
      },
      {
        "name": "chartmuseum_url",
        "short": "u",
        "long": "chartmuseum-url",
        "env_var": "DOIT_CHARTMUSEUM_URL",
        "type": str,
        "default": None,
        "help": f"ChartMuseum URL.",
      },
      {
        "name": "chartmuseum_basic_auth_user",
        "short": "U",
        "long": "chartmuseum-basic-auth-user",
        "env_var": "DOIT_CHARTMUSEUM_BASIC_AUTH_USER",
        "type": str,
        "default": None,
        "help": f"ChartMuseum basic auth username.",
      },
      # TODO: mask secret
      {
        "name": "chartmuseum_basic_auth_pass",
        "short": "P",
        "long": "chartmuseum-basic-auth-pass",
        "env_var": "DOIT_CHARTMUSEUM_BASIC_AUTH_PASS",
        "type": str,
        "default": None,
        "help": f"ChartMuseum basic auth user password.",
      },
    ],
  }


def get_common_werf_params():
  return [
    {
      "name": "werf_version",
      "short": "v",
      "long": "werf-version",
      "env_var": "DOIT_WERF_VERSION",
      "type": str,
      "default": DEFAULT_WERF_VERSION,
      "help": f"Werf version and release channel. Default: {DEFAULT_WERF_VERSION}",
    },
    {
      "name": "werf_color_mode",
      "long": "werf-color-mode",
      "env_var": "DOIT_WERF_COLOR_MODE",
      "type": str,
      "default": DEFAULT_WERF_COLOR_MODE,
      "help": f"Werf color mode. Default: {DEFAULT_WERF_COLOR_MODE}",
    },
    {
      "name": "werf_global_ci_url",
      "long": "werf-global-ci-url",
      "env_var": "DOIT_WERF_GLOBAL_CI_URL",
      "type": str,
      "default": DEFAULT_WERF_GLOBAL_CI_URL,
      "help": f"Werf global.ci_url value. Default: {DEFAULT_WERF_GLOBAL_CI_URL}",
    },
  ]


def get_common_extra_params():
  return [
    {
      "name": "extra_args",
      "short": "a",
      "long": "extra-arg",
      "type": list,
      "default": [],
      "help": f"Extra arg for werf command, can be specified multiple times.",
    },
    {
      "name": "extra_env_vars",
      "short": "v",
      "long": "extra-env-var",
      "type": list,
      "default": [],
      "help": f'Extra env vars for werf command, can be specified multiple times. Example: "--extra-env-var ENV_VAR=env_val".',
    },
  ]


################################################################################
# Action generators
################################################################################


def action_prepare_werf(werf_version, werf_color_mode):
  return [
    f'export WERF_LOG_COLOR_MODE="{werf_color_mode}"',
    f'source <(multiwerf use {werf_version})',
  ]


def action_export_env_vars(env_vars):
  result = []
  for env_var in env_vars:
    env_var = env_var.split("=", 1)
    result += (f'export {env_var[0]}="{env_var[1]}"')
  return result


def action_werf_lint(env, chart, extra_args):
  return [f'werf helm lint --env "{env}" --set "{chart}.enabled=true" {" ".join(extra_args)}']


def action_werf_render(env, chart, extra_args):
  return [
    (
      f'werf helm render --env "{env}" --set "{chart}.enabled=true" {" ".join(extra_args)}'
      f' | tail -n +6 | grep -vE "(^\#)|(werf.io/version)"'
      f' | yq -sy --indentless "sort_by(.apiVersion,.kind,.metadata.name)[]"'
    )
  ]


def action_werf_package_chart(chart_path, extra_args):
  return [f'helm package "{chart_path}" -d "{CHART_PACKAGE_DIR}" {" ".join(extra_args)}']


def action_werf_publish_chart_package(package_path, chartmuseum_url, chartmuseum_basic_auth_user,
                                      chartmuseum_basic_auth_pass, extra_args):
  return [
    (
      f'curl {" ".join(extra_args)} -sSL --post301 --data-binary "@{package_path}"'
      f' --user "{chartmuseum_basic_auth_user}:{chartmuseum_basic_auth_pass}"'
      f' "{urllib.parse.urljoin(chartmuseum_url, "/api/charts")}"'
    )
  ]


def action_werf_download_root_chart_dependencies(extra_args):
  return [f'werf helm dependency update {" ".join(extra_args)}']


def action_werf_download_nested_chart_dependencies(chart_path, extra_args):
  return [f'werf helm dependency update --helm-chart-dir "{chart_path}" {" ".join(extra_args)}']


################################################################################
# Utilities
################################################################################


def get_chart_paths(chart_names, chart_root_dir):
  chart_paths = []
  for chart_name in chart_names:
    chart_paths += (os.path.join(chart_root_dir, chart_name))
  return chart_paths


def get_all_chart_paths(chart_root_dir):
  possible_chart_dirs = glob.glob(os.path.join(chart_root_dir, "*"))
  return list(filter(lambda path: os.path.isdir(path), possible_chart_dirs))


def get_all_chart_names(chart_root_dir):
  chart_dirs = get_all_chart_paths(chart_root_dir)
  return list(map(lambda dir: os.path.basename(dir), chart_dirs))


def get_chart_package_paths(chart_package_filenames, chart_package_dir):
  package_paths = []
  for package_filename in chart_package_filenames:
    package_paths += (os.path.join(chart_package_dir, package_filename))
  return package_paths


def get_all_chart_package_paths(chart_package_dir):
  return glob.glob(os.path.join(chart_package_dir, "*.tgz"))


def abort_if_param_undefined(params):
  for param_name, param_value in params.items():
    if param_value is None:
      print(f'[ERROR] Required parameter "{param_name}" is not specified. Aborting.')
      sys.exit(1)
