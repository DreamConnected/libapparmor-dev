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
- dosfstools
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
endef

# Ubuntu shares cloud-init profile with Debian.
UBUNTU_CLOUD_INIT_USER_DATA_TEMPLATE=$(DEBIAN_CLOUD_INIT_USER_DATA_TEMPLATE)

# This is the cloud-init user-data profile for openSUSE Tumbleweed.
define OPENSUSE_tumbleweed_CLOUD_INIT_USER_DATA_TEMPLATE
$(CLOUD_INIT_USER_DATA_TEMPLATE)
packages:
- attr
- autoconf
- autoconf-archive
- automake
- bison
- dbus-1-devel
- dejagnu
- dosfstools
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
- python3-devel
- python311-devel
- swig
endef
