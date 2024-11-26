# This file is read by image-garden when spread is allocating test machines.
# All the package installation happens through cloud-init profiles defined
# below.

# This is the cloud-init user-data profile for all Debian systems. Note that it
# is an extension of the default profile necessary for operation of
# image-garden.
define DEBIAN_CLOUD_INIT_USER_DATA_TEMPLATE
$(CLOUD_INIT_USER_DATA_TEMPLATE)
packages:
- attr
- autoconf
- autoconf-archive
- automake
- bison
- build-essential
- dejagnu
- flake8
- flex
- gettext
- libdbus-1-dev
- libtool
- liburing-dev
- pkg-config
- python3-all-dev
- python3-gi
- python3-notify2
- python3-psutil
- python3-setuptools
- python3-tk
- python3-ttkthemes
- swig
runcmd:
- apt clean
endef

# Ubuntu shares cloud-init profile with Debian.
UBUNTU_CLOUD_INIT_USER_DATA_TEMPLATE=$(DEBIAN_CLOUD_INIT_USER_DATA_TEMPLATE)

# On openSUSE Leap the default gcc and python are very old. We can use more
# recent version of Python quite easily but perl extension module system does
# not want us to modify the CC that's baked into perl and all my attempts at
# using gcc-14 have failed.
define OPENSUSE_CLOUD_INIT_USER_DATA_TEMPLATE
$(CLOUD_INIT_USER_DATA_TEMPLATE)
packages:
- attr
- autoconf
- autoconf-archive
- automake
- bison
- dbus-1-devel
- dejagnu
- flex
- gcc
- gcc-c++
- gettext
- gobject-introspection
- libtool
- liburing2-devel
- make
- pkg-config
- python3-flake8
- python3-notify2
- python3-psutil
- python3-setuptools
- python3-setuptools
- python3-tk
- python311
- python311-devel
- swig
endef

# On openSUSE tumbleweed the set of packages may drift towards more recent
# versions more rapidly than on Leap but the moment we want to, for example,
# move to Python 3.13, we can define a separate entry with different package
# set or perhaps with $(patsubst)-computed package set.
OPENSUSE_tumbleweed_CLOUD_INIT_USER_DATA_TEMPLATE=$(OPENSUSE_CLOUD_INIT_USER_DATA_TEMPLATE)
