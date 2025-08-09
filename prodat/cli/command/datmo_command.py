from prodat.core.util.i18n import get as __
from prodat.cli.command.base import BaseCommand

class prodatCommand(BaseCommand):
    def __init__(self, cli_helper):
        super(prodatCommand, self).__init__(cli_helper)

    def usage(self):
        self.cli_helper.echo(__("argparser", "cli.prodat.usage"))

    def prodat(self):
        self.parse(["--help"])
        return True
