
#include <tunables/global>

@{SNAP_NAME}="smt"
@{SNAP_REVISION}="7"
@{PROFILE_DBUS}="snap_2esmt_2esmt"
@{INSTALL_DIR}="/{,var/lib/snapd/}snap"

profile "snap.smt.smt" (attach_disconnected,mediate_deleted,complain) {
  # set file rules so that exec() inherits our profile unless there is
  # already a profile for it (eg, snap-confine)
  / rwkl,
  /** rwlkm,
  /** pix,

  capability,
  change_profile,
  dbus,
  network,
  mount,
  remount,
  umount,
  pivot_root,
  ptrace,
  signal,
  unix,


}
