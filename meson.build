project(
  'user-service-manager',
  version: '0.1.0-dev',
  meson_version: '>= 1.3.0',
)

gnome = import('gnome')
python = import('python').find_installation('python3')
conf = configuration_data()
conf.set('PYTHON', python.full_path())

subdir('src')
subdir('data')
subdir('po')

test(
  'unit-tests',
  python,
  args: ['-m', 'unittest', 'discover', '-s', meson.project_source_root() / 'tests', '-v'],
  env: {
    'PYTHONPATH': meson.project_source_root() + '/src:' + meson.project_source_root(),
  },
)
