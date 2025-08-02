import re
import base64
import json
from hashlib import sha256
from utils.custom_exceptions import IPBlockedByWAF

class WAFSolver:

    @staticmethod
    def solve(html_content):

        def fix_base64_padding(b64_string):
            padding_needed = (4 - len(b64_string) % 4) % 4
            return b64_string + ('=' * padding_needed)

        # Extract wci
        pattern = r'<p\s+[^>]*id=["\']wci["\'][^>]*class=["\']([^"\']+)["\']'
        match = re.search(pattern, html_content)
        if not match:
            raise ValueError("wci not found in HTML")
        wci = match.group(1)

        # Extract cs
        pattern = r'<p\s+[^>]*id=["\']cs["\'][^>]*class=["\']([^"\']+)["\']'
        match = re.search(pattern, html_content)
        if not match:
            raise ValueError("cs not found in HTML")
        cs = match.group(1)

        # decode json from base64
        c = json.loads(base64.b64decode(fix_base64_padding(cs)))

        prefix = base64.b64decode(c['v']['a'])
        expect = base64.b64decode(c['v']['c']).hex()

        for i in range(1000000):
            tried = sha256(prefix + str(i).encode('utf-8')).hexdigest()
            if expect == tried:
                d = base64.b64encode(str(i).encode('utf-8')).decode('utf-8')
                c['d'] = d
                result = json.dumps(c)
                cookie = base64.b64encode(result.encode('utf-8')).decode('utf-8')
                return {wci: cookie}

        raise IPBlockedByWAF
