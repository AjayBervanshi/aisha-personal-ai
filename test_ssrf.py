import urllib.request
import urllib.parse
import socket
import ipaddress

def test_url(url_str):
    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid scheme: {parsed.scheme}")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Missing hostname")

        # Resolve IP
        ip_addr = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_addr)

        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            raise ValueError(f"Blocked IP: {ip_addr}")
    except Exception as e:
        print(f"SSRF blocked URL {url_str}: {e}")
        return False

    class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            parsed_new = urllib.parse.urlparse(newurl)
            if parsed_new.scheme not in ("http", "https"):
                raise urllib.error.URLError(f"Invalid redirect scheme: {parsed_new.scheme}")
            try:
                new_host = parsed_new.hostname
                if not new_host:
                    raise urllib.error.URLError("Missing hostname in redirect")
                new_ip_addr = socket.gethostbyname(new_host)
                new_ip = ipaddress.ip_address(new_ip_addr)
                if new_ip.is_private or new_ip.is_loopback or new_ip.is_link_local or new_ip.is_multicast:
                    raise urllib.error.URLError(f"Blocked IP in redirect: {new_ip_addr}")
            except Exception as e:
                raise urllib.error.URLError(f"SSRF redirect blocked: {e}")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    req = urllib.request.Request(url_str, method="GET")
    opener = urllib.request.build_opener(SafeRedirectHandler())
    try:
        with opener.open(req, timeout=5) as r:
            return True
    except urllib.error.URLError as e:
        print(f"HTTP request failed: {e}")
        return False

print("Testing http://localhost")
test_url("http://localhost")
print("Testing http://127.0.0.1")
test_url("http://127.0.0.1")
print("Testing http://169.254.169.254")
test_url("http://169.254.169.254")
print("Testing file:///etc/passwd")
test_url("file:///etc/passwd")
print("Testing http://example.com")
test_url("http://example.com")
