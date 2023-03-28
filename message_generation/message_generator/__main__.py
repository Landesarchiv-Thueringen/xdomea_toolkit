import os

from .config import ConfigParser
from .xdomea_message_generator import XdomeaMessageGenerator

generator_config = ConfigParser.parse_config('config/generator_config.xml', 'config/generator_config.xsd')
message_generator = XdomeaMessageGenerator(generator_config)
message_generator.generate_xdomea_messages()
# pause until user confirmation on windows
if os.name == 'nt':
    print('\n')
    os.system("pause")
