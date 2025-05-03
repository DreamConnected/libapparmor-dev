# Tooling Requirements

The AppArmor userspace needs to be buildable and usable on very old systems. The oldest systems we are currently targeting use GCC 5, Python 3.5, and Linux 4.15. This imposes some limitations on available language features, listed below.

## C/C++

C/C++ code must only use language features up to C11/C++11 with GNU extensions (the latest that GCC 5 supports).

In addition, dependencies are also limited to ones available on older systems. For example, `libapparmor` and `apparmor_parser` use flex and bison (with GNU extensions, as opposed to plain lex and yacc), but are restricted to features available in flex 2.6.0 and bison 3.0.4. (The bison version constraint is more likely to come up, as flex's latest release is 2.6.4). This is because later versions of bison are not available on old systems, even if bison generates code compilable with very old C/C++ standards.

`apparmor_parser` is built against `libapparmor` and should be able to build against an older system `libapparmor`. The parser should try to avoid using functions added more recently to `libapparmor` without some kind of fallback, and situations requiring omission of a fallback warrant extra discussion.

## Python

Python code must be runnable under versions from Python 3.5 to the latest Python 3. This means only using language features available in Python 3.5, and not using any modules deprecated or removed in the latest Python 3.

## Linux Kernel

Tooling that interacts with the kernel side of AppArmor, such as `apparmor_parser`, must work with a Linux 4.15 kernel (with reduced functionality acceptable in cases such as a profile mediating a kernel feature like io_uring which was not around yet in Linux 4.15). This means, for example, including fallbacks when attempting to use newer kernel features that may not be available on older systems.

# Submitting Profiles

The writer of a profile will generally have more knowledge about the application being confined and its specific behaviors than the reviewers of an MR that proposes adding the new profile, or a sysadmin who would read the profile in order to make site-specific adjustments. Thus, a profile is better if it contains a brief description of how it was tested, which would help reviewers and sysadmins understand which application functionality was exercised under confinement and to illuminate potential gaps in a profile and its testing. More detailed testing steps, as well as an overview of what the application is supposed to do, can be placed in the description field of the MR proposed for the profile. This will help MR reviewers evaluate the profile and provide additional context in the git logs for future reference when the MR is merged.
