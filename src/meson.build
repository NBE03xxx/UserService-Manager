package_dir = python.get_install_dir() / 'user_service_manager'

python.install_sources(
  'user_service_manager/__init__.py',
  'user_service_manager/main.py',
  subdir: 'user_service_manager',
)

foreach directory : ['domain', 'ports', 'adapters', 'application', 'infrastructure', 'presentation']
  python.install_sources(
    'user_service_manager' / directory / '__init__.py',
    subdir: 'user_service_manager' / directory,
  )
endforeach

python.install_sources('user_service_manager/domain/models.py', subdir: 'user_service_manager/domain')
python.install_sources('user_service_manager/domain/discovery.py', subdir: 'user_service_manager/domain')
python.install_sources('user_service_manager/domain/journal.py', subdir: 'user_service_manager/domain')
python.install_sources('user_service_manager/domain/editing.py', subdir: 'user_service_manager/domain')
python.install_sources('user_service_manager/ports/service_backend.py', subdir: 'user_service_manager/ports')
python.install_sources('user_service_manager/ports/discovery.py', subdir: 'user_service_manager/ports')
python.install_sources('user_service_manager/ports/registration.py', subdir: 'user_service_manager/ports')
python.install_sources('user_service_manager/ports/commands.py', subdir: 'user_service_manager/ports')
python.install_sources('user_service_manager/ports/journal.py', subdir: 'user_service_manager/ports')
python.install_sources('user_service_manager/ports/editing.py', subdir: 'user_service_manager/ports')
python.install_sources('user_service_manager/adapters/mock_backend.py', subdir: 'user_service_manager/adapters')
python.install_sources('user_service_manager/adapters/path_policy.py', subdir: 'user_service_manager/adapters')
python.install_sources('user_service_manager/adapters/filesystem_scanner.py', subdir: 'user_service_manager/adapters')
python.install_sources('user_service_manager/adapters/gio_systemd_query.py', subdir: 'user_service_manager/adapters')
python.install_sources('user_service_manager/adapters/gio_systemd_commands.py', subdir: 'user_service_manager/adapters')
python.install_sources('user_service_manager/adapters/systemd_journal.py', subdir: 'user_service_manager/adapters')
python.install_sources('user_service_manager/adapters/registration_repositories.py', subdir: 'user_service_manager/adapters')
python.install_sources('user_service_manager/adapters/unit_file_store.py', subdir: 'user_service_manager/adapters')
python.install_sources('user_service_manager/adapters/systemd_unit_verifier.py', subdir: 'user_service_manager/adapters')
python.install_sources('user_service_manager/application/catalog.py', subdir: 'user_service_manager/application')
python.install_sources('user_service_manager/application/discovery_service.py', subdir: 'user_service_manager/application')
python.install_sources('user_service_manager/application/command_service.py', subdir: 'user_service_manager/application')
python.install_sources('user_service_manager/application/journal_service.py', subdir: 'user_service_manager/application')
python.install_sources('user_service_manager/application/editing_service.py', subdir: 'user_service_manager/application')
python.install_sources('user_service_manager/infrastructure/preferences.py', subdir: 'user_service_manager/infrastructure')
python.install_sources('user_service_manager/presentation/application.py', subdir: 'user_service_manager/presentation')

install_data(
  'user_service_manager/presentation/style.css',
  'user_service_manager/presentation/style-dark.css',
  install_dir: package_dir / 'presentation',
)

install_data(
  'user_service_manager/presentation/assets/cafe-coffee-line-v4.png',
  install_dir: package_dir / 'presentation' / 'assets',
)

configure_file(
  input: 'user-service-manager.in',
  output: 'user-service-manager',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
)
