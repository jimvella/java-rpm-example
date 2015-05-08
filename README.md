#Java linux service RPM packaging example featuring spring boot

I would like to demystify how to package java services for Fedora, Red Hat and CentOS.
There are a few build system plugins that I think end up obfuscating what is a fairly straight forward
process with the native packaging tool `rpmbuild`.

RPM is a great way to streamline deployments and upgrades. It enables better configuration management either on its own
or in conjunction with YUM, kickstart, puppet or chef. [PhoenixSevers](http://martinfowler.com/bliki/PhoenixServer.html) become straight forward.

##Build, package and deploy
    mvn clean install

on a distribution set up for rpm packaging

    cp target/myservice-0.0.1-SNAPSHOT-rpm.tar.gz ~/rpmbuild/SOURCES
    rpmbuild -ba target/myservice.spec

    #as root
    yum install rpmbuild/RPMS/myservice-0.0.1-SNAPSHOT-rpm
    service myservice start

http://localhost:8080

##Packaging concepts
###rpmbuild
The inputs for `rpmbuild` are a tarball of the source, and the specfile. Ideally it unpacks the source and simply runs

    make test
    make install

Whilst we could have `rpmbuild` invoke maven, the maven assembly plugin allows us to satisfy the tarball input for `rpmbuild`,
whist simultaneously allowing us to add the additional files required for a linux service as well as decoupling the maven build process
from the RPM packaging process.

The specfile is a short script that contains package metadata including package dependencies,
instructions to build, the files that comprise the package, and how to deploy, upgrade and remove.

###Anatomy of a linux service
A linux service is an independent concept from RPM. We will need an understanding of how to structure a service before we can package it.
I like to think about services in terms of concerns.

####User
It is accepted as a good security practice that applications are not run as the root user in order to insulate the OS from
buggy or malicious code. Typically a service user is maintained for the purpose of running the service.

####Files
There is a [standard that defines which files go where](http://www.tldp.org/LDP/intro-linux/html/sect_03_01.html).
In short, a service will typically have the following files:

* `/etc/rc.d/init.d/myservice` - service initialisation script
* `/etc/myservice/*`  - configuration
* `/usr/share/myservice/*`    - files (i.e. the jar/s)
* `/var/log/myservice/*`  - logs

It's important to follow this standard as these are the locations a system administrator will expect. Note that there is a layer
of abstraction in the RPM specfile in the form of [autoconfig style macros](https://fedoraproject.org/wiki/Packaging:RPMMacros).

####Initialisation script
The initialisation script runs the service as a [daemon](http://en.wikipedia.org/wiki/Daemon_%28computing%29) as the appropriate user.
It also allows the service to be managed via the OS's service management interface. i.e.

    service myservice start

The implementation follows the [Fedora wiki](https://fedoraproject.org/wiki/Packaging:SysVInitScript)

####Start on boot
A linux service will be registered with the start on boot system, such that the administrator can configure whether a service should start on
boot on not through the OS's service management interface. i.e.

    #enable start on boot
    chkconfig myservice on

###Applying RPM packaging to Java
####The Maven Assembly
The assembly is managed with the maven plugins: maven-jar-plugin, maven-resources-plugin, maven-assembly-plugin, and comprises the following resources

* __src/main/resources/myservice.properties__
With spring boot, its very handy to have application and logging configuration in _src/main/resources_ in order to use 'mvn spring-boot:run'.
However by default, maven will embed any _src/main/resources_ files into the jar. Embedded properties can confuse administrators once the application
has been deployed to production. To avoid confusion I think all configuration should be externalised to _/etc/myservice_. This is achieved by filtering
configuration from the jar via the maven-jar-plugin, and pulling into the assembly with the maven-assembly-plugin.
_myservice.properties_ is recycled from _src/main/resources_, whilst an independent _logback.xml_ is maintained in _src/main/rpm-resources_. It is possible
for a single default config to work in multiple environments by not using fully qualified domain names. Short names combined with environment specific
DNS resolver config (_/etc/resolv.conf_) should be sufficient. As for logging, separate configurations for development and a deployed services are necessary.
Where a development logging config will be to the console and verbose, the production logging config should log to _/var/log/myservice_,
feature a sensible rotation scheme, include a syslog appender and not be overly verbose.

* __src/assembly/java-rpm-example.spec__
Whether or not to include a dependency for a specific java implementation is a bit tricky. Ideally, our app won't care what java it's run on,
but without a dependency the package won't be able to check for and install if necessary a sufficient implementation for it to run.
If a java dependency is included, the package will refuse to be installed without it, even if another java implementation is available.
If the app is an internal app, I think its a good idea to include the dependency as it will simplify deployment.
Otherwise the specfile follows the [Fedora wiki](https://fedoraproject.org/wiki/Packaging:SysVInitScript).

* __src/main/rpm-resources/**__
Includes the init script and logging configuration. Spring boot has a facility for both the properties and logback config to be passed to the executable jar
as arguments which are leveraged in the init script. The init script otherwise follows the the [Fedora wiki](https://fedoraproject.org/wiki/Packaging:SysVInitScript).

* __src/assembly/rpm-assembly.xml__
Assembly descriptor to bundles the RPM resources with the spring boot executable jar for rpmbuild. Filters the specfile to insert the maven pom version.

###The RPM lifecycle
####install
On installation the RPM will

* Deploy the files
* Create the service user if the service user does not exist
* Register the service with `chkconfig`

####update

* Updates the files
  Note that for files marked as __config(noreplace)__ there is special behavior:
  * If the config file has local edits, but the same default config is in both RPMs, the local edits are maintained
  * If the config file has local edits, and there is a new default config in the new RPM, the local edits are maintaied and the new default config is place in `.new`
  Its up to the administrator to manually reconcile the old existing config with the new default.
  * If the config file has no local edits, and there is a new default config in the new RPM, the config is updated.
* After the files are update, and if the service is running, the service is restarted.

Note that the package must be a new version otherwise RPM will refuse to update. This feature allows confident reporting of the deployed version, but
won't work with the SNAPSHOT versioning scheme of the maven release plugin. Adopting a [continuous delivery](http://www.slideshare.net/wakaleo/continuous-deliverywithmaven) / deployment approach where every build is versioned
is more amenable to RPM updates.

####remove

* stops the service
* un-registers the service with `chkconfig`
* deletes all of the files owned by the RPM

##Issues and future improvements
* The example init script is sysv and should be updated to systemd
* The specfile has a section for a changelog. The current example simply leaves the section empoty. Perhaps the release notes could be pulled from Jira.
