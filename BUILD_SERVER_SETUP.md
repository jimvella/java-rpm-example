# Setup CentOS 7 on virtual box as a RPM build server

Create a [CentOS](https://www.centos.org/) virtual machine on [virtual box](https://www.virtualbox.org/)

1. Define a new linux guest in virtual box
1. Insert the CentOS dvd iso into the virtual dvd drive
1. Enable networking. After installation, by default CentOS 7 networking is disabled.
    ```
    vi /etc/sysconfig/network-scripts/ifcfg-enp0s3
    #change ONBOOT=no to ONBOOT=yes
    systemctl restart network
    ```
	
1. (optional) Add port forwarding to allow ssh connections for convenience, i.e. 2222 to 22 on the CentOS guest

Install preferred vcs

    yum install git

Install Maven

    yum install maven
	
Setup CentOS for building RPMs

1. Create a build user
    ```
    useradd builduser
    ```
	
1. Install RPM tools
    ```
    yum install rpm-build rpmdevtools
    ```
	
1. Setup build directory structure
    ```
    su - builduser
    rpmdev-setuptree
    ```
	
Build java-rpm-example

    git clone https://github.com/Chomeh/java-rpm-example.git
	cd java-rpm-example
	mvn install
	cd target
	cp myservice-0.1-rpm.tar.gz ~/rpmbuild/SOURCES
	rpmbuild -ba java-rpm-example.spec
	
Deplopy java-rpm-example

	#as root
	yum install ~builduser/rpmbuild/RPMS/noarch/myservice-0.1-1.el7.centos.noarch.rpm
	service myservice start
	tail -f /var/log/myservice/myservice.log
	


	 
