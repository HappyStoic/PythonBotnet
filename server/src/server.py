@click.command()
@click.option(
    "--configuration_dir",
    "-c",
    type=click.Path(),
    required=True,
    help="Path to configuration dir with all yaml config files",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Debug mode. Sets debug logger and allows not to configure certs",
)
def main(configuration_dir, debug):
	pass

if __name__ == "__main__":
	main()
