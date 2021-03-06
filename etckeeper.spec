%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif

%{!?_pkgdocdir: %global _pkgdocdir %{_docdir}/%{name}-%{version}}

%if 0%{?fedora} || 0%{?rhel} > 5
%global with_bzr 1
%endif

%if 0%{?fedora}
%global with_dnf 1
%global dnf_is_mandatory 1
%global dnf_uses_python3 1
%endif

%if 0%{?rhel} >= 7
%global with_dnf 1
%endif

%if 0%{?fedora} || 0%{?rhel} >= 7
%global with_systemd 1
%endif

Name:      etckeeper
Version:   1.18.5
Release:   5%{?dist}
Summary:   Store /etc in a SCM system (git, mercurial, bzr or darcs)
Group:     Applications/System
License:   GPLv2+
URL:       http://etckeeper.branchable.com/
Source0:   https://github.com/joeyh/etckeeper/archive/%{version}/%{name}-%{version}.tar.gz
Source1:   README.fedora
Patch0:    etckeeper-makefile-remove-python-plugins.patch
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
BuildRequires: python-markdown
Requires:  git >= 1.5.4
Requires:  perl-interpreter
Requires:  crontabs
%if 0%{?dnf_is_mandatory}
Requires:  %{name}-dnf = %{version}-%{release}
%endif # dnf_is_mandatory
%if 0%{?with_systemd}
BuildRequires:  systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
%endif # with_systemd

%description
The etckeeper program is a tool to let /etc be stored in a git,
mercurial, bzr or darcs repository. It hooks into yum to automatically
commit changes made to /etc during package upgrades. It tracks file
metadata that version control systems do not normally support, but that
is important for /etc, such as the permissions of /etc/shadow. It's
quite modular and configurable, while also being simple to use if you
understand the basics of working with version control.

The default backend is git, if want to use a another backend please
install the appropriate tool (mercurial, darcs or bzr).
To use bzr as backend, please also install the %{name}-bzr package.

To start using the package please read %{_pkgdocdir}/README.


%if 0%{?with_bzr}
%package bzr
Summary:  Support for bzr with etckeeper
Group:    Applications/System
BuildRequires: python2-devel
BuildRequires: bzr
Requires: %{name} = %{version}-%{release}
Requires: bzr

%description bzr
This package provides a bzr backend for etckeeper, if you want to use
etckeeper with bzr backend, install this package.
%endif # with_bzr


%if 0%{?with_dnf}
%package dnf
Summary:  DNF plugin for etckeeper support
Group:    Applications/System
%if 0%{?dnf_uses_python3}
BuildRequires: python3-devel
%else
BuildRequires: python2-devel
%endif # dnf_uses_python3
BuildRequires: dnf
BuildRequires: dnf-plugins-core
Requires: %{name} = %{version}-%{release}
Requires: dnf
Requires: dnf-plugins-core

%description dnf
This package provides a DNF plugin for etckeeper. If you want to use
etckeeper with DNF, install this package.
%endif # with_dnf


%prep
%setup -q
%patch0 -p1
# we set yum here, so the yum plugin gets built, and change that to
# dnf later, if needed
sed -e 's|HIGHLEVEL_PACKAGE_MANAGER=.*|HIGHLEVEL_PACKAGE_MANAGER=yum|' \
    -e 's|LOWLEVEL_PACKAGE_MANAGER=.*|LOWLEVEL_PACKAGE_MANAGER=rpm|' \
    -i etckeeper.conf
sed -e 's|^prefix=.*|prefix=%{_prefix}|' \
    -e 's|^bindir=.*|bindir=%{_bindir}|' \
    -e 's|^etcdir=.*|etcdir=%{_sysconfdir}|' \
    -e 's|^mandir=.*|mandir=%{_mandir}|' \
    -e 's|^vardir=.*|vardir=%{_localstatedir}|' \
    -e 's|^INSTALL=.*|INSTALL=install -p|' \
    -e 's|^CP=.*|CP=cp -pR|' \
    -i Makefile
%if 0%{?with_systemd}
sed -e 's|^systemddir=.*|systemddir=%{_unitdir}|' \
    -i Makefile
%endif
# move each plugin in its own subdirectory, so each has its own build/
# directory
mkdir bzr-plugin ; mv etckeeper-bzr bzr-plugin
mkdir dnf-plugin ; mv etckeeper-dnf dnf-plugin
cp -av %{SOURCE1} .


%build
make %{?_smp_mflags}

%if 0%{?with_bzr}
pushd bzr-plugin
%{__python2} etckeeper-bzr/__init__.py build
popd
%endif

%if 0%{?with_dnf}
pushd dnf-plugin
%if 0%{?dnf_uses_python3}
%{__python3} etckeeper-dnf/etckeeper.py build
%else
%{__python2} etckeeper-dnf/etckeeper.py build
%endif
popd
%endif

%if 0%{?fedora} || 0%{?rhel} >= 7
# the binary in python-markdown has been renamed
markdown_py -f README.html README.md
%else
markdown -f README.html README.md
%endif


%install
rm -rf %{buildroot}
make install DESTDIR=%{buildroot}

%if 0%{?with_bzr}
pushd bzr-plugin
%{__python2} etckeeper-bzr/__init__.py install -O1 --skip-build --root %{buildroot}
popd
%endif

%if 0%{?with_dnf}
pushd dnf-plugin
%if 0%{?dnf_uses_python3}
%{__python3} etckeeper-dnf/etckeeper.py install -O1 --skip-build --root %{buildroot}
%else
%{__python2} etckeeper-dnf/etckeeper.py install -O1 --skip-build --root %{buildroot}
%endif
popd

%if 0%{?dnf_is_mandatory}
sed -e 's|HIGHLEVEL_PACKAGE_MANAGER=.*|HIGHLEVEL_PACKAGE_MANAGER=dnf|' \
    -i %{buildroot}%{_sysconfdir}/%{name}/%{name}.conf
%endif
%endif

install -D -p debian/cron.daily %{buildroot}%{_sysconfdir}/cron.daily/%{name}
install -d  %{buildroot}%{_localstatedir}/cache/%{name}

# on RHEL < 7, move the completion file back to /etc/bash_completion.d
%if !(0%{?fedora} || 0%{?rhel} >= 7)
install -d %{buildroot}%{_sysconfdir}/bash_completion.d
mv %{buildroot}%{_datadir}/bash-completion/completions/%{name} \
  %{buildroot}%{_sysconfdir}/bash_completion.d/%{name}
%endif

# remove unit files if not used (note: /lib/systemd/system is the
# original, hardcoded location from the etckeeper Makefile)
%if !0%{?with_systemd}
rm %{buildroot}/lib/systemd/system/%{name}.service
rm %{buildroot}/lib/systemd/system/%{name}.timer
%endif


%clean
rm -rf %{buildroot}


%post
if [ $1 -gt 1 ] ; then
   %{_bindir}/%{name} update-ignore
fi
%if 0%{?with_systemd}
%systemd_post %{name}.service
%systemd_post %{name}.timer
%endif # with_systemd


%preun
%if 0%{?with_systemd}
%systemd_preun %{name}.service
%systemd_preun %{name}.timer
%endif # with_systemd


%postun
%if 0%{?with_systemd}
%systemd_postun %{name}.service
%systemd_postun %{name}.timer
%endif # with_systemd


%files
%doc README.html README.fedora
%if 0%{?_licensedir:1}
%license GPL
%else
%doc GPL
%endif # licensedir
%{_bindir}/%{name}
%{_mandir}/man8/%{name}.8*
%dir %{_sysconfdir}/%{name}
%{_sysconfdir}/%{name}/*.d
%{_sysconfdir}/%{name}/daily
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.conf
%{_sysconfdir}/cron.daily/%{name}
%if 0%{?fedora} || 0%{?rhel} >= 7
%dir %{_datadir}/bash-completion
%dir %{_datadir}/bash-completion/completions
%{_datadir}/bash-completion/completions/%{name}
%else
%dir %{_sysconfdir}/bash_completion.d
%{_sysconfdir}/bash_completion.d/%{name}
%endif
%dir %{_prefix}/lib/yum-plugins
%{_prefix}/lib/yum-plugins/%{name}.*
%dir %{_sysconfdir}/yum/pluginconf.d
%config(noreplace) %{_sysconfdir}/yum/pluginconf.d/%{name}.conf
%{_localstatedir}/cache/%{name}
%if 0%{?with_systemd}
%{_unitdir}/%{name}.service
%{_unitdir}/%{name}.timer
%endif # with_systemd


%if 0%{?with_bzr}
%files bzr
%{python2_sitelib}/bzrlib/plugins/%{name}
%{python2_sitelib}/bzr_%{name}-*.egg-info
%endif # with_bzr


%if 0%{?with_dnf}
%files dnf
%if 0%{?dnf_uses_python3}
%{python3_sitelib}/dnf-plugins/%{name}.py
%exclude %{python3_sitelib}/dnf-plugins/__init__.py
%{python3_sitelib}/dnf-plugins/__pycache__/%{name}.*
%exclude %{python3_sitelib}/dnf-plugins/__pycache__/__init__.*
%{python3_sitelib}/dnf_%{name}-*.egg-info
%else
%{python2_sitelib}/dnf-plugins/%{name}.py*
%exclude %{python2_sitelib}/dnf-plugins/__init__.py*
%{python2_sitelib}/dnf_%{name}-*.egg-info
%endif # dnf_uses_python3
%endif # with_dnf


%changelog
* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.18.5-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Thu Jul 13 2017 Petr Pisar <ppisar@redhat.com> - 1.18.5-4
- perl dependency renamed to perl-interpreter
  <https://fedoraproject.org/wiki/Changes/perl_Package_to_Install_Core_Modules>

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.18.5-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Mon Dec 19 2016 Miro Hrončok <mhroncok@redhat.com> - 1.18.5-2
- Rebuild for Python 3.6

* Tue Aug 23 2016 Thomas Moschny <thomas.moschny@gmx.de> - 1.18.5-1
- Update to 1.18.5.

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.18.3-3
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Wed Mar  2 2016 Thomas Moschny <thomas.moschny@gmx.de> - 1.18.3-2
- Move completion file back to /etc/bash_completion.d on EPEL<7.

* Mon Feb 22 2016 Thomas Moschny <thomas.moschny@gmx.de> - 1.18.3-1
- Update to 1.18.3.
- Bash completions have been moved to /usr/share/bash-completion.

* Wed Feb  3 2016 Thomas Moschny <thomas.moschny@gmx.de> - 1.18.2-4
- Do not own /etc/bash_completion.d on Fedora and EPEL>=7.
- Drop %%defattr.

* Wed Feb 03 2016 Fedora Release Engineering <releng@fedoraproject.org> - 1.18.2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Tue Nov 10 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.18.2-2
- Rebuilt for https://fedoraproject.org/wiki/Changes/python3.5

* Sat Oct 24 2015 Thomas Moschny <thomas.moschny@gmx.de> - 1.18.2-1
- Update to etckeeper 1.18.2.
- Depend on dnf for F22+ (rhbz#1229131).
- Minor changelog fixes.

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.18.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Thu Apr 23 2015 Thomas Moschny <thomas.moschny@gmx.de> - 1.18.1-2
- Fix HTML generation from markdown (rhbz#1213776).

* Thu Mar 26 2015 Thomas Moschny <thomas.moschny@gmx.de> - 1.18.1-1
- Update to 1.18.1.
- Add missing dependency on python3-devel for dnf plugin on F23+.

* Fri Mar 20 2015 Thomas Moschny <thomas.moschny@gmx.de> - 1.18-1
- Update to 1.18.
- Update upstream URLs.
- Package DNF plugin.
- Slightly modernize spec file.

* Thu Dec 18 2014 Thomas Moschny <thomas.moschny@gmx.de> - 1.14-2
- Disable bzr plugin on epel5.

* Fri Sep  5 2014 Thomas Moschny <thomas.moschny@gmx.de> - 1.14-1
- Update to 1.14.

* Fri Aug 15 2014 Thomas Moschny <thomas.moschny@gmx.de> - 1.13-1
- Update to 1.13.

* Sun Jun 22 2014 Thomas Moschny <thomas.moschny@gmx.de> - 1.12-1
- Update to 1.12.
- Format README.md.

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.11-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Thu Dec 19 2013 Thomas Moschny <thomas.moschny@gmx.de> - 1.11-1
- Update to 1.11.

* Sat Nov  9 2013 Thomas Moschny <thomas.moschny@gmx.de> - 1.10-1
- Update to 1.10.

* Thu Sep 12 2013 Thomas Moschny <thomas.moschny@gmx.de> - 1.9-1
- Update to 1.9.

* Sun Aug 18 2013 Thomas Moschny <thomas.moschny@gmx.de> - 1.7-1
- Update to 1.7.
- Define (if undefined) and use _pkgdocdir macro (rhbz#993741).

* Tue Jul 30 2013 Thomas Moschny <thomas.moschny@gmx.de> - 1.6-1
- Update to 1.6.

* Sat Jul 27 2013 Thomas Moschny <thomas.moschny@gmx.de> - 1.5-1
- Update to 1.5.

* Sat Jul 27 2013 Jóhann B. Guðmundsson <johannbg@fedoraproject.org> - 1.4-2
- Add a missing requirement on crontabs to spec file

* Sun Jun 23 2013 Thomas Moschny <thomas.moschny@gmx.de> - 1.4-1
- Update to 1.4.

* Fri May 10 2013 Thomas Moschny <thomas.moschny@gmx.de> - 1.3-1
- Update to 1.3.

* Wed Feb 13 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.64-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Sun Sep 23 2012 Thomas Moschny <thomas.moschny@gmx.de> - 0.64-1
- Update to 0.64.

* Thu Jul 19 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.63-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Mon Jun  4 2012 Thomas Moschny <thomas.moschny@gmx.de> - 0.63-1
- Update to 0.63.

* Tue Mar 13 2012 Thomas Moschny <thomas.moschny@gmx.de> - 0.62-2
- Add missing dependency on perl (bz 798563).

* Tue Mar 13 2012 Thomas Moschny <thomas.moschny@gmx.de> - 0.62-1
- Update to 0.62.

* Tue Jan 17 2012 Thomas Moschny <thomas.moschny@gmx.de> - 0.61-1
- Update to 0.61.

* Fri Jan 13 2012 Thomas Moschny <thomas.moschny@gmx.de> - 0.60-1
- Update to 0.60.

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.58-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Thu Dec  1 2011 Thomas Moschny <thomas.moschny@gmx.de> - 0.58-1
- Update to 0.58.

* Wed Nov  9 2011 Thomas Moschny <thomas.moschny@gmx.de> - 0.57-1
- Update to 0.57.

* Wed Aug 17 2011 Thomas Moschny <thomas.moschny@gmx.de> - 0.56-2
- Rebuilt for trailing slash bug of rpm-4.9.1

* Thu Jul 21 2011 Thomas Moschny <thomas.moschny@gmx.de> - 0.56-1
- Update to 0.56.

* Fri Jun 24 2011 Thomas Moschny <thomas.moschny@gmx.de> - 0.55-1
- Update to 0.55.

* Wed Jun  1 2011 Thomas Moschny <thomas.moschny@gmx.de> - 0.54-1
- Update to 0.54.
- Add patch for bz 709487.

* Mon Mar 28 2011 Thomas Moschny <thomas.moschny@gmx.de> - 0.53-1
- Update to 0.53.
- Run update-ignore on package upgrade (bz 680632).

* Wed Feb  9 2011 Thomas Moschny <thomas.moschny@gmx.de> - 0.52-1
- Update to 0.52.
- Include a README.fedora (bz 670934).

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.51-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Mon Jan  3 2011 Thomas Moschny <thomas.moschny@gmx.de> - 0.51-1
- Update to 0.51.
- etckeeper has been moved out of sbin.

* Sat Dec 11 2010 Thomas Moschny <thomas.moschny@gmx.de> - 0.50-2
- Don't package INSTALL.

* Wed Oct 27 2010 Thomas Moschny <thomas.moschny@gmx.de> - 0.50-1
- Update to 0.50.
- Change %%define -> %%global.

* Fri Sep 17 2010 Thomas Moschny <thomas.moschny@gmx.de> - 0.49-2
- Adjust minimum required version of GIT.
- egg-info files are not created automatically on RHEL5.

* Wed Sep 15 2010 Thomas Moschny <thomas.moschny@gmx.de> - 0.49-1
- Update to 0.49.
- Remove obsolete patch.

* Fri Sep  3 2010 Thomas Moschny <thomas.moschny@gmx.de> - 0.48-1
- Update to 0.48.
- Don't list /etc/etckeeper/*.d directories twice in %%files.
- Add patch from upstream that fixes bz 588086.

* Wed Jul 21 2010 David Malcolm <dmalcolm@redhat.com> - 0.41-2
- Rebuilt for https://fedoraproject.org/wiki/Features/Python_2.7/MassRebuild

* Sat Sep 12 2009 Bernie Innocenti <bernie@codewiz.org> - 0.41-1
- Update to 0.41
- Add missing directory ownerships

* Sat Sep 12 2009 Bernie Innocenti <bernie@codewiz.org> - 0.40-3
- Make the bzr subpackage builddepend on python-devel

* Wed Sep 09 2009 Terje Rosten <terje.rosten@ntnu.no> - 0.40-2
- Package is noarch
- Rpmlint clean
- Random cleanup
- Ship cache dir in package
- bzr subpackage
- Add bzr to buildreq

* Sat Sep 05 2009 Bernie Innocenti <bernie@codewiz.org> - 0.40-1
- Update to 0.40

* Sun Jun 14 2009 Bernie Innocenti <bernie@codewiz.org> - 0.37-1
- Update to 0.37
- Change license tag to GPLv2+

* Fri Feb 27 2009 Jimmy Tang <jtang@tchpc.tcd.ie> - 0.33-4
- fix up initial install to make directory in /var/cache/etckeeper
- install the etckeeper daily cron job
- define some config files that shouldn't be replaced, should the hooks
in commit.d, init.d etc... saved and not blown away? if so they can
defined as config files. etckeeper should record the changes anyway.

* Wed Feb 25 2009 Jimmy Tang <jtang@tchpc.tcd.ie> - 0.32-1
- yum etckeeper plugin is now apart of this package

* Tue Feb 24 2009 Jimmy Tang <jtang@tchpc.tcd.ie> - 0.31-1
- initial package
