# Invoice Template Parsers Package
# Each parser outputs a normalized JSON schema for Indian GST invoices

from .base_parser import BaseParser, NormalizedInvoice, LineItem, ValidationResult
from .amazon_parser import AmazonParser
from .flipkart_parser import FlipkartParser
from .meesho_parser import MeeshoParser
from .vmart_parser import VMartParser
from .acevector_parser import AceVectorParser
from .myntra_parser import MyntraParser
from .fashnear_parser import FashnearParser
from .jiomart_parser import JioMartParser
from .generic_parser import GenericParser

__all__ = [
    'BaseParser',
    'NormalizedInvoice', 
    'LineItem',
    'ValidationResult',
    'AmazonParser',
    'FlipkartParser', 
    'MeeshoParser',
    'VMartParser',
    'AceVectorParser',
    'MyntraParser',
    'FashnearParser',
    'JioMartParser',
    'GenericParser'
]
