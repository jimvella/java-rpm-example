# Java linux service RPM packaging example featuring spring boot

I would like to demystify how to package java services for Fedora, Red Hat and CentOS.
There are a few build system plugins that I think end up obfuscating what is a fairly straight forward
process with the OS's native packaging tool `rpmbuild`.

RPM is a great way to streamline deployments and upgrades. It enables better configuration management either on its own
or in conjunction with YUM, kickstart, puppet or chef. [PhoenixSevers](http://martinfowler.com/bliki/PhoenixServer.html) become straight forward.

## Build, package and deploy
    mvn install

On a [distribution set up for rpm packaging](BUILD_SERVER_SETUP.md)

    cp target/myservice-0.1-rpm.tar.gz ~/rpmbuild/SOURCES
    rpmbuild -ba target/java-rpm-example.spec

    #as root
    yum install rpmbuild/RPMS/noarch/myservice-0.1-1.el7.centos.noarch.rpm
    service myservice start

[http://localhost:8080](http://localhost:8080)

## Packaging concepts
### rpmbuild
`rpmbuild` is the OS tool for building RPMs. The inputs for `rpmbuild` are a tarball of the source, and the spec file. Ideally it unpacks the source and simply runs

    make test
    make install

Whilst we could have `rpmbuild` invoke maven, the maven assembly plugin allows us to satisfy the tarball input for `rpmbuild`,
whist simultaneously allowing us to add the additional files required for a linux service as well as decoupling the maven build process
from the RPM packaging process.

The spec file is a short script that contains package metadata including package dependencies,
instructions to build, the files that comprise the package, and how to deploy, update and remove.

### Anatomy of a linux service
A linux service is an independent concept from RPM. We will need an understanding of how to structure a service before we can package it.
I like to think about services in terms of concerns.

#### User
It is accepted as a good security practice that applications are not run as the root user in order to insulate the OS from
buggy or malicious code. Typically a service user is maintained for the purpose of running the service.

#### Files
There is a [standard that defines which files go where](http://www.tldp.org/LDP/intro-linux/html/sect_03_01.html).
In short, a service will typically have the following files:

    /etc/rc.d/initd/myservice	                #service initialisation script if using SysV
    /usr/lib/systemd/system/myservice.service   #systemd service file if using systemd
    /etc/myservice/*                			#configuration
    /usr/share/myservice/*		                #files (i.e. the jar/s)
    /var/log/myservice/*	                	#logs

It's important to follow this standard as these are the locations a system administrator will expect. Note that there is a layer
of abstraction in the RPM spec file in the form of [autoconfig style macros](https://fedoraproject.org/wiki/Packaging:RPMMacros).

#### Initialisation script
The initialisation script runs the service as a [daemon](http://en.wikipedia.org/wiki/Daemon_%28computing%29), as the appropriate user.
It also allows the service to be managed via the OS's service management interface. i.e.

    service myservice start

The implementation follows the [Fedora wiki](https://fedoraproject.org/wiki/Packaging:SysVInitScript)

#### Start on boot
A linux service will be registered with the 'start on boot' system `chkconfig`, such that the administrator can configure whether a service should start on
boot on not through the OS's service management interface. i.e.

    #enable start on boot
    chkconfig myservice on 

On systems using systemd, use `systemctl enable myservice` instead.

### Applying RPM packaging to Java
The src files contributing to packaging:

    src/pom.xml							#Plugin configuration
    src/main/rpm-resources/config/*		#Config files to be added to the assembly
    src/main/rpm-resources/initd/*		#Initialisation files to be added to the assembly if using SysV
    src/main/rpm-resources/systemd/*	#Initialisation files to be added to the assembly if using systemd
    src/main/assembly/rpm-assembly.xml	#Assembly descriptor
    src/main/assembly/myservice.spec	#RPM spec file


#### The Maven Assembly
The structure of files in the assembly are arbitrary in that they ultimately mapped by the spec file to OS locations. The chosen structure of the assembly is

    config
    initd or systemd
    jar

Use initd or systemd depending on whether your system uses SysV style init scripts or systemd services.

The maven-resources-plugin is used to insert maven properties into the spec file, the version being of particular importance.

##### Spring Boot
If your application uses Spring Boot, replace the variable placeholders like ${project.artifactId} to look like @project.artifactId@ or variable replacement won't work!

The maven-jar-plugin is used to exclude configuration from the jar.
With spring boot, its very handy to have application and logging configuration in `src/main/resources` in order to use `mvn spring-boot:run`.
However by default, maven will include any `src/main/resources` files into the jar. Hidden in the jar, this configuration
can confuse administrators once the application has been deployed to production. To avoid confusion I think all configuration
should be externalised to `/etc/myservice`.

Production logging config `src/main/rpm-resources/config/logback.xml` is maintained separately from the `mvn spring-boot:run` development
config `src/main/resources/config/logback.xml`. Where a development logging config will be to the console and verbose,
the production logging will log to `/var/log/myservice`, feature a sensible rotation scheme, ideally include a syslog appender and not be overly verbose.
Whilst the same strategy can be applied to `myservice.properties`, It is possible for a single default config to work in multiple
environments by not using fully qualified domain names. Short names combined with environment specific DNS resolver configurations (`/etc/resolv.conf`)
should be sufficient. Adopting this strategy, the assembly descriptor 'cherry picks' `src/main/resources/myservice.properties` into the assembly's
`config` in lieu of needing to maintain a separate `src/main/rpm-resources/myservice.properties`.

#### The spec file
Deciding whether or not to include a package dependency for a specific java implementation is a bit tricky. Ideally, our app won't care what java it's run on,
but without a dependency the package won't be able to check for and install if necessary a sufficient implementation for it to run.
If a java dependency is included, the package will refuse to be installed without it, even if another java implementation is available.
If the app is an internal app, I think its a good idea to include the dependency as it will simplify deployment.
Otherwise the spec file follows the [Fedora wiki](https://fedoraproject.org/wiki/Packaging:SysVInitScript).
Make sure to customise the spec file to use SysV or systemd (see the comments inside of it).

### The RPM lifecycle
An understanding of RPM behaviour, particularly with how configuration files are managed for updates is important to avoid deployment gotchas for java programmers.

#### install

    yum install myservice

* Deploy the files.
* Create the service user if the service user does not exist.
* Register the service with `chkconfig`

#### update

    yum update myservice

* Updates the files. Note that for files marked in the spec file with __config(noreplace)__ there is special behavior:
  * If the config file has local edits, but the same default config is in both RPMs, the local edits are maintained
  * If the config file has local edits, and there is a new default config in the new RPM, the local edits are maintained and the new default config is place in `.new`.
  Its up to the administrator to manually reconcile the old existing config with the new default.
  * If the config file has no local edits, and there is a new default config in the new RPM, the config is updated.
* After the files are update, and if the service is running, the service is restarted.

Note that the package must be a new version otherwise RPM will refuse to update. This feature allows confident reporting of the deployed version, but
won't work with the SNAPSHOT versioning scheme of the maven release plugin. Adopting a [continuous delivery](http://www.slideshare.net/wakaleo/continuous-deliverywithmaven) approach where every build is versioned
is more amenable to RPM updates.

#### remove

    yum remove myservice

* Stops the service.
* Un-registers the service with `chkconfig`.
* Deletes all of the files owned by the RPM.

## Issues and future improvements
* The [fedora java packaging HOWTO](https://fedorahosted.org/released/javapackages/doc/) prefers individual dependencies are packaged rather than the spring boot uber jar approach. The fedora way may be the future, but until packages are readily available I think packaging the spring boot uber jar as a linux service is the most pragmatic approach.
* Could register a shutdown hook for graceful shutdown.
* Could include monitoring, i.e. spring-boot-actuator or Dropwizard metrics
* The spec file has a section for a changelog. The current example simply leaves the section empty. Perhaps the release notes could be pulled from Jira.
