app_id = 'io.github.NBE03xxx.UserServiceManager'

install_data(app_id + '.desktop', install_dir: get_option('datadir') / 'applications')
install_data(app_id + '.metainfo.xml', install_dir: get_option('datadir') / 'metainfo')

gnome.compile_schemas(
  build_by_default: true,
  depend_files: files(app_id + '.gschema.xml'),
)
install_data(
  app_id + '.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)
