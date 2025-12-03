import sys

class IngressMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_INGRESS_PATH', '')

        # Debug logging to stdout (captured by HA logs)
        print(f"DEBUG: IngressMiddleware - HTTP_X_INGRESS_PATH: {script_name!r}", file=sys.stdout)
        print(f"DEBUG: IngressMiddleware - ORIGINAL SCRIPT_NAME: {environ.get('SCRIPT_NAME', '')!r}", file=sys.stdout)
        print(f"DEBUG: IngressMiddleware - ORIGINAL PATH_INFO: {environ.get('PATH_INFO', '')!r}", file=sys.stdout)

        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

            print(f"DEBUG: IngressMiddleware - NEW SCRIPT_NAME: {environ['SCRIPT_NAME']!r}", file=sys.stdout)
            print(f"DEBUG: IngressMiddleware - NEW PATH_INFO: {environ['PATH_INFO']!r}", file=sys.stdout)

        return self.app(environ, start_response)
