SNMP server
===========

|MIT license badge|

Description:
------------
Simple SNMP server in pure Python

Usage with pytest:
------------------

It is possible to use snmpserver as pytest plugin. This option requires Python >=3.6.

The fixture ``snmpserver`` has the ``host`` and ``port`` attributes (which can be set via environment variables ``PYTEST_SNMPSERVER_HOST`` and ``PYTEST_SNMPSERVER_PORT``), along with the ``expect_request`` method:

::

  def test_request_replies_correctly(snmpserver):
      snmpserver.expect_request("1.3.6.1.2.1.2.2.1.2", "some description")
      command = shlex.split(f'{snmpget_command} {snmpserver.host}:{snmpserver.port} IF-MIB::ifDescr')
      p = subprocess.Popen(command, stdout=subprocess.PIPE)
      p.wait()
      assert 'IF-MIB::ifDescr some description' == p.stdout.read().decode('utf-8').strip()


Standalone usage:
-----------------

It is also possible to use standalone version of SNMP server, which works as an echo server if no config is passed. This version supports Python 2 and 3.

::

  Standalone usage: snmp_server.py [-h] [-p PORT] [-c CONFIG] [-d] [-v]

  SNMP server

  optional arguments:
    -h, --help            show this help message and exit
    -p PORT, --port PORT  port (by default 161 - requires root privileges)
    -c CONFIG, --config CONFIG
                          OIDs config file
    -d, --debug           run in debug mode
    -v, --version         show program's version number and exit

**Examples:**

::

  # ./snmp_server.py -p 12345
  SNMP server listening on 0.0.0.0:12345
  # ./snmp_server.py
  SNMP server listening on 0.0.0.0:161

Without config file SNMP server works as a simple SNMP echo server:

::

  # snmpget -v 2c -c public 0.0.0.0:161 1.2.3.4.5.6.7.8.9.10.11
  iso.2.3.4.5.6.7.8.9.10.11 = STRING: "1.2.3.4.5.6.7.8.9.10.11"

It is possible to create a config file with values for specific OIDs.

Config file - is a Python script and must have DATA dictionary with string OID keys and values.

Values can be either ASN.1 types (e.g. :code:`integer(...)`, :code:`octet_string(...)`, etc) or any Python lambda/functions (with single argument - OID string), returning ASN.1 type.

::

  DATA = {
    '1.3.6.1.4.1.1.1.0': integer(12345),
    '1.3.6.1.4.1.1.2.0': bit_string('\x12\x34\x56\x78'),
    '1.3.6.1.4.1.1.3.0': octet_string('test'),
    '1.3.6.1.4.1.1.4.0': null(),
    '1.3.6.1.4.1.1.5.0': object_identifier('1.3.6.7.8.9'),
    # notice the wildcards:
    '1.3.6.1.4.1.1.6.*': lambda oid: octet_string('* {}'.format(oid)),
    '1.3.6.1.4.1.1.?.0': lambda oid: octet_string('? {}'.format(oid)),
    '1.3.6.1.4.1.2.1.0': real(1.2345),
    '1.3.6.1.4.1.3.1.0': double(12345.2345),
  }

::

  # ./snmp-server.py -c config.py
  SNMP server listening on 0.0.0.0:161

With config file :code:`snmpwalk` command as well as :code:`snmpget` can be used:

::

  # snmpwalk -v 2c -c public 0.0.0.0:161 .1.3.6.1.4.1
  iso.3.6.1.4.1.1.1.0 = INTEGER: 12345
  iso.3.6.1.4.1.1.2.0 = BITS: 12 34 56 78 3 6 10 11 13 17 19 21 22 25 26 27 28
  iso.3.6.1.4.1.1.3.0 = STRING: "test"
  iso.3.6.1.4.1.1.4.0 = NULL
  iso.3.6.1.4.1.1.5.0 = OID: iso.3.6.7.8.9
  iso.3.6.1.4.1.1.6.4294967295 = STRING: "* 1.3.6.1.4.1.1.6.4294967295"
  iso.3.6.1.4.1.1.9.0 = STRING: "? 1.3.6.1.4.1.1.9.0"
  iso.3.6.1.4.1.2.1.0 = Opaque: Float: 1.234500
  iso.3.6.1.4.1.3.1.0 = Opaque: Float: 12345.234500
  iso.3.6.1.4.1.4.1.0 = No more variables left in this MIB View (It is past the end of the MIB tree)

Also :code:`snmpset` command can be used:

::

  # snmpset -v2c -c public 0.0.0.0:161 .1.3.6.1.4.1.1.3.0 s "new value"
  iso.3.6.1.4.1.1.3.0 = STRING: "new value"
  #
  # snmpget -v2c -c public 0.0.0.0:161 .1.3.6.1.4.1.1.3.0
  iso.3.6.1.4.1.1.3.0 = STRING: "new value"

Web Interface
------------

The SNMP server now includes a web interface for easy configuration management. The web interface allows you to view and modify the SNMP server configuration through a browser.

Running the Web Interface
~~~~~~~~~~~~~~~~~~~~~~~~

To start the web interface:

.. code-block:: bash

    python web-interface.py

By default, the web interface runs on port 9999. Access it at http://localhost:9999

Configuration Format
~~~~~~~~~~~~~~~~~~

The web interface expects configurations in Python format with a ``DATA`` dictionary containing OID mappings. Example:

.. code-block:: python

    # SNMP Server Configuration
    DATA = {
        # Simple string OID - System Description
        '1.3.6.1.2.1.1.1.0': 'Example SNMP Server',  # Will be converted to OCTET_STRING

        # System uptime
        '1.3.6.1.2.1.1.3.0': 123456,  # Will be converted to TIMETICKS

        # Simple integer value
        '1.3.6.1.2.1.1.4.0': 42,  # Will be converted to INTEGER

        # Basic counter
        '1.3.6.1.2.1.2.1.0': 1000,  # Will be converted to COUNTER32

        # IP address as string
        '1.3.6.1.2.1.3.1.0': '192.168.1.1',  # Will be converted to IPADDRESS

        # Function that returns dynamic value
        '1.3.6.1.2.1.4.1.0': lambda oid: len(oid)
    }

Features
~~~~~~~~

- Live configuration editing through web browser
- Automatic validation of configuration syntax
- Configuration backup creation before updates
- Automatic type conversion for SNMP values
- Real-time updates (no server restart required)

Value Types
~~~~~~~~~~

The configuration supports these basic Python types that are automatically converted to SNMP types:

- Strings → OCTET_STRING
- Integers → INTEGER
- IP address strings → IPADDRESS
- Functions → Dynamic values (must take one OID argument)

Security Note
~~~~~~~~~~~~

The web interface is intended for local development and testing. For production use, consider:

- Running behind a reverse proxy
- Adding authentication
- Restricting access to trusted networks
- Using HTTPS

License:
--------
Released under `The MIT License`_.

.. |MIT license badge| image:: http://img.shields.io/badge/license-MIT-brightgreen.svg
.. _The MIT License: https://github.com/delimitry/snmp-server/blob/master/LICENSE
