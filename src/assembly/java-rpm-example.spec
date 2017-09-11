Name:		${project.artifactId}
Version:	${project.version}
Release:	1%{?dist}
Summary:	${project.description}

Group:		Applications/System			
License:	MIT	
URL:		https://github.com/Chomeh/java-rpm-example.git		
Source0:	%{name}-%{version}-rpm.tar.gz	
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:	noarch
#Requires:	java-1.7.0-openjdk
Requires(post): chkconfig
Requires(preun): chkconfig
# This is for /sbin/service
Requires(preun): initscripts
# This is for /sbin/service
Requires(postun): initscripts

%description
${description}

%define __jar_repack %{nil}

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/%{_sysconfdir}/%{name}
mkdir -p %{buildroot}/%{_initddir}
mkdir -p %{buildroot}/%{_datadir}/%{name}
mkdir -p %{buildroot}/%{_localstatedir}/log/%{name}
cp config/* %{buildroot}/%{_sysconfdir}/%{name} 
# For Sysv
cp initd/* %{buildroot}/%{_initddir}/ 
# For systemd
## sed -e "s/__DESCRIPTION__/%{name}/" -e "s|__JAR__|%{_datadir}/%{name}/%{name}.jar|" -e "s|__USER__|%{name}|" -e "s|__CONFIGFILE__|%{_sysconfdir}/%{name}/application.properties|" < systemd/myservice.service.template > systemd/%{name}.service
## cp systemd/%{name}.service %{buildroot}/usr/lib/systemd/system/%{name}.service
cp *.jar %{buildroot}/%{_datadir}/%{name}/%{name}.jar

%clean
rm -rf %{buildroot}

%files
%defattr(-,%{name},%{name},-)
%{_datadir}/%{name}/*
# For SysV
%attr(755,root,root) %{_initddir}/*
# For systemd
## %attr(644,root,root) /usr/lib/systemd/system/%{name}.service
%{_localstatedir}/log/*
%config(noreplace) %attr(600,%{name},%{name}) %{_sysconfdir}/%{name}/*

%pre
getent group %{name} > /dev/null || groupadd -r %{name}
getent passwd %{name} > /dev/null || useradd -r -g %{name} %{name} -s /sbin/nologin

%post
# This adds the proper /etc/rc*.d links for the script
# For SysV
/sbin/chkconfig --add %{name}
# For systemd
## systemctl daemon-reload
## systemctl enable %{name}

%preun
if [ $1 -eq 0 ] ; then
    # For SysV
    /sbin/service %{name} stop >/dev/null 2>&1
    /sbin/chkconfig --del %{name}
    # For systemd
    ## systemctl stop %{name}
    ## systemctl disable %{name}
fi

%postun
if [ "$1" -ge "1" ] ; then
    # For SysV
    /sbin/service %{name} condrestart >/dev/null 2>&1 || :
    # For systemd
    ## systemctl restart %{name}
fi


%changelog

