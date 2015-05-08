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

[http://localhost:8080](http://localhost:8080)

##Packaging concepts
###rpmbuild
`rpmbuild` is the OS tool for building RPMs. The inputs for `rpmbuild` are a tarball of the source, and the specfile. Ideally it unpacks the source and simply runs

    make test
    make install

Whilst we could have `rpmbuild` invoke maven, the maven assembly plugin allows us to satisfy the tarball input for `rpmbuild`,
whist simultaneously allowing us to add the additional files required for a linux service as well as decoupling the maven build process
from the RPM packaging process.

The specfile is a short script that contains package metadata including package dependencies,
instructions to build, the files that comprise the package, and how to deploy, update and remove.

###Anatomy of a linux service
A linux service is an independent concept from RPM. We will need an understanding of how to structure a service before we can package it.
I like to think about services in terms of concerns.

####User
It is accepted as a good security practice that applications are not run as the root user in order to insulate the OS from
buggy or malicious code. Typically a service user is maintained for the purpose of running the service.

####Files
There is a [standard that defines which files go where](http://www.tldp.org/LDP/intro-linux/html/sect_03_01.html).
In short, a service will typically have the following files:

* `/etc/rc.d/initd/myservice` - service initialisation script
* `/etc/myservice/*`  - configuration
* `/usr/share/myservice/*`    - files (i.e. the jar/s)
* `/var/log/myservice/*`  - logs

It's important to follow this standard as these are the locations a system administrator will expect. Note that there is a layer
of abstraction in the RPM specfile in the form of [autoconfig style macros](https://fedoraproject.org/wiki/Packaging:RPMMacros).

####Initialisation script
The initialisation script runs the service as a [daemon](http://en.wikipedia.org/wiki/Daemon_%28computing%29), as the appropriate user.
It also allows the service to be managed via the OS's service management interface. i.e.

    service myservice start

The implementation follows the [Fedora wiki](https://fedoraproject.org/wiki/Packaging:SysVInitScript)

####Start on boot
A linux service will be registered with the start on boot system `chkconfig`, such that the administrator can configure whether a service should start on
boot on not through the OS's service management interface. i.e.

    #enable start on boot
    chkconfig myservice on

###Applying RPM packaging to Java
The src files contributing to packaging:
* `src/pom.xml` - Plugin configuration
* `src/main/rpm-resources/config/*` - Config files to be added to the assembly
* `src/main/rpm-resources/initd/*` - Initialisation files to be added to the assembly
* `src/main/assembly/rpm-assembly.xml` - Assembly descriptor
* `src/main/assembly/myservice.spec` - RPM specfile

####The Maven Assembly
The structure of the assembly produced is

```
+-- config
+-- initd
+-- jar
```

The maven-resources-plugin is used to filter / insert maven properties into the specfile, the verison being of particular importance.

The maven-jar-plugin is used to exclude configuration from the jar.
With spring boot, its very handy to have application and logging configuration in `src/main/resources` in order to use `mvn spring-boot:run`.
However by default, maven will include any `src/main/resources` files into the jar. Hidden in the jar, this configuration
can confuse administrators once the application has been deployed to production. To avoid confusion I think all configuration
should be externalised to `/etc/myservice`.

A package / production logging config `src/main/rpm-resources/config/logback.xml` is maintained separately from the `mvn spring-boot:run` development
config `src/main/resources/config/logback.xml`. Where a development logging config will be to the console and verbose,
the production logging config should log to `/var/log/myservice`, feature a sensible rotation scheme, ideally include a syslog appender and not be overly verbose.
Whilst the same strategy can be applied to `myservice.properties`, It is possible for a single default config to work in multiple
environments by not using fully qualified domain names. Short names combined with environment specificDNS resolver config (`/etc/resolv.conf`)
should be sufficient. Adopting this strategy, the assembly descriptor 'cherry picks' `src/main/resources/myservice.properties` into the assembly's
`config` in lieu of having to maintain a separate `src/main/rpm-resources/myservice.properties`.

#### The specfile
Deciding whether or not to include a package dependency for a specific java implementation is a bit tricky. Ideally, our app won't care what java it's run on,
but without a dependency the package won't be able to check for and install if necessary a sufficient implementation for it to run.
If a java dependency is included, the package will refuse to be installed without it, even if another java implementation is available.
If the app is an internal app, I think its a good idea to include the dependency as it will simplify deployment.
Otherwise the specfile follows the [Fedora wiki](https://fedoraproject.org/wiki/Packaging:SysVInitScript).

###The RPM lifecycle
An understanding of RPM behaviour, particularly with how configuration files are managed for updates is important to avoid deployment gotchas for java programmers.

####install

    yum install myservice.rpm

* Deploy the files
* Create the service user if the service user does not exist
* Register the service with `chkconfig`

####update

    yum update myservice.rpm

* Updates the files
  Note that for files marked as __config(noreplace)__ there is special behavior:
  * If the config file has local edits, but the same default config is in both RPMs, the local edits are maintained
  * If the config file has local edits, and there is a new default config in the new RPM, the local edits are maintaied and the new default config is place in `.new`.
  Its up to the administrator to manually reconcile the old existing config with the new default.
  * If the config file has no local edits, and there is a new default config in the new RPM, the config is updated.
* After the files are update, and if the service is running, the service is restarted.

Note that the package must be a new version otherwise RPM will refuse to update. This feature allows confident reporting of the deployed version, but
won't work with the SNAPSHOT versioning scheme of the maven release plugin. Adopting a [continuous delivery](http://www.slideshare.net/wakaleo/continuous-deliverywithmaven) / deployment approach where every build is versioned
is more amenable to RPM updates.

####remove

    yum remove myservice.rpm

* stops the service
* un-registers the service with `chkconfig`
* deletes all of the files owned by the RPM

###YUM repositories
TODO

##Issues and future improvements
* The example init script is sysv and should be updated to systemd
* The specfile has a section for a changelog. The current example simply leaves the section empty. Perhaps the release notes could be pulled from Jira.
