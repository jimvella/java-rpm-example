# java-rpm-example
Java linux service RPM packaging example featuring spring boot

I would like to demystify how to package java services for Fedora, Red Hat and CentOS.
There are a few build system plugins that I think end up obfuscating what is a fairly straight forward
process with the native packaging tool 'rpmbuild'.

RPM is a great way to streamline deployments and upgrades. It enables better configuration management either on its own
or in conjunction with YUM, kickstart, puppet or chef. [PhoenixSevers](http://martinfowler.com/bliki/PhoenixServer.html) become straight forward.

##Build and Package
    mvn clean install

on a distribution set up for rpm packaging

    cp target/myservice-0.0.1-SNAPSHOT-rpm.tar.gz ~/rpmbuild/SOURCES
    rpmbuild -ba target/myservice.spec

##rpmbuild
The input, or the interface for rpmbuild is a tarball of the source. Ideally it unpacks the source and simply runs

    make test
    make install

Whilst we could have rpmbuild invoke maven, the maven assembly plugin allows us to satisfy this 'interface' to rpmbuild,
simultaneously allowing us to add the additional files required for a linux service whilst decoupling the maven build process
from the rpm packaging process.

rpmbuild is driven by the specfile. The specfile is a short script that contains package metadata including package dependencies,
instructions to build, the files that comprise the package, and how to deploy, upgrade and remove.

##Anatomy of a linux service
A linux service is an independent concept from RPM. We will need an understanding of how to structure a service before we can package it.
I like to think about services in terms of concerns.

###User
It is accepted as a good security practice that applications are not run as the root user in order to insulate the OS from
buggy or malicious code. Typically a service user is maintained for the purpose of running the service.
User creation is automated by RPM.

###Files
There is a standard that defines which files go where, see http://www.tldp.org/LDP/intro-linux/html/sect_03_01.html.
In short, a service will typically have the following files:

* __/etc/rc.d/init.d/myservice__ service initialisation script
* __/etc/myservice/*__  - configuration
* __/usr/share/myservice/*__    - files (i.e. the jar/s)
* __/var/log/myservice/*__  - logs

It's important to follow this standard as these are locations a system administrator will expect. Note that there is a layer
of abstraction in the RPM specfile in the form of autoconfig style macros.

###Initialisation script
The initialisation script runs the service as a daemon http://en.wikipedia.org/wiki/Daemon_%28computing%29 as the appropriate user.
It also allows the service to be managed via the OS's service management interface. i.e.

    service myservice start

See https://fedoraproject.org/wiki/Packaging:SysVInitScript

###Start on boot
A linux service will be registered with the start on boot system, such that the administrator can configure whether a service should start on
boot on not through the OS's service management interface. i.e.

    chkconfig myservice on

##Applying RPM packaging to Java
###The Maven Assembly
The assembly is managed with the maven plugins: maven-jar-plugin, maven-resources-plugin, maven-assembly-plugin, and comprises the following resources

* __src/main/resources/myservice.properties__
With spring boot, its very handy to have application and logging configuration in _src/main/resources_ in order to use 'mvn spring-boot:run'.
However by default, maven will embed any src/main/resources files into the jar. Embedded properties can confuse administrators once the application
has been deployed to production. To avoid confusion I think configuration should be externalised to /etc/myservice. This is achieved by filtering
configuration from the jar via the maven-jar-plugin, and pulling into the assembly with the maven-assembly-plugin.

myservice.properties is recycled from src/main/resources, whilst an independent logback.xml is maintained in src/main/rpm-resources. It is possible
for a single default config to work in multiple environments by not using fully qualified domain names. Short names combined with environment specific
DNS resolver config (/etc/resolv.conf) should be sufficient. As for logging, separate configurations for dev and a deployed service are necessary.
Where a dev logging config will be to the console and verbose, the production logging config should log to /var/log/myservice,
feature a sensible rotation scheme, include a syslog appender and not be overly verbose.

* __src/assembly/java-rpm-example.spec__
Whether or not to include a dependency for a specific java implementation is a bit tricky. Ideally, our app won't care what java it's run on,
but without a dependency the package won't be able to check for and install if necessary a sufficient implementation for it to run.
If a java dependency is included, the package will refuse to be installed without it, even if another java implementation is available.
If the app is an internal app, I think its a good idea to include the dependency as it will simplify deployment.
Otherwise the specfile follows the fedora guide, see https://fedoraproject.org/wiki/Packaging:SysVInitScript.

* __src/main/rpm-resources/**__
Includes the init script and logging configuration. Spring boot has a facility for both the properties and logback config to be passed to the executable jar
as arguments which are leveraged in the init script. The init script otherwise follows the Fedora guide. See https://fedoraproject.org/wiki/Packaging:SysVInitScript.

* __src/assembly/rpm-assembly.xml__
Assembly descriptor to bundles the rpm resources with the spring boot executable jar for rpmbuild. Filters the specfile to insert the maven pom version.

##The RPM lifecycle
### install
On installation the RPM will

* Deploy the files
* Create the service user if the service user does not exist
* Register the service with chkconfig

### update

* Updates the files
Note that for files marked as config(noreplace) there is special behavior.
 If the config file has local edits, but the same default config is in both RPMs, the local edits are maintained
 If the config file has local edits, and there is a new default config in the new RPM, the local edits are maintaied and the new default config is place in .new
 Its up to the administrator to manually reconcile the old existing config with the new default.
 If the config file has no local edits, and there is a new default config in the new RPM, the config is updated.
* after the files are update, and if the service is running, the service is restarted.
Note that the package must be a new version otherwise RPM will refuse to update. This feature allows confident reporting of the deployed version, but
won't work with the SNAPSHOT versioning of the maven release plugin. Adopting a continuous delivery / deployment approach where every build is versioned
is more amenable to RPM updates.

### remove

* stops the service
* unregisters the service with chkconfig
* deletes all of the files owned by the RPM

##Issues and future improvements

* The specfile has a section for a changelog. The current example simply leaves the section empoty. Perhaps the release notes could be pulled from Jira.
