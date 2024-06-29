Server configuration:

The server provides the ROACH2 with its IP settings, a boot image via TFTP, and
a filesystem for the PowerPC via NFS. It is assumed that all required system
packages (e.g. nfs-kernel-server , nfs-common , etc., but which may differ among
distributions) are installed.

To set up DHCP and TFTP using dnsmasq:

1. Identify a network interface on the server through which it can offer DHCP
to the ROACH2. Set its IP settings to have a static configuration. Bring
down and back up the interface if necessary. I configured interface eno2
to have a static IP address 10.66.192.32, and the ROACH2 should always obtain
the address 10.66.192.36 from the server. See Gary about allocating static IPs.

2. Create the path /srv/roach2_boot on the server filesystem.

3. Clone https://github.com/sma-wideband/r2dbe.git into a temporary path.
We only need the contents in the /support subdirectory here.

4. Do an attribute-preserving copy of the boot image doing something like
<cp -rfp support/boot /srv/roach2_boot>

5. Do an attribute-preserving copy of the tarballed filesystem by doing some-
thing like <cp -fp support/r2dbe-debian-fs.tar.gz /srv/roach2_boot>

6. In /srv/roach2_boot do <tar xvfz r2dbe-debian-fs.tar.gz> which will create
a directory called debian_stable_devel/

7. Rename/move debian_stable_devel/ by doing <mv debian_stable_devel root>

8. Now we are done with the cloned git repository, delete it if you want to.

9. Edit the server configuration file at /etc/exports and add the line:
/srv/roach2_boot 10.66.192.0/20(rw,subtree_check,no_root_squash,insecure)

10. Effect the changes by doing <exportfs -r> and verify that it is successful
by doing <showmount -e>

11. Edit /etc/dnsmasq.conf to include the following lines (see example file):
no-resolv
dhcp-host=02:44:01:02:13:07,10.66.192.36
dhcp-boot=uImage
enable-tftp
tftp-root=/srv/roach2_boot/boot
dhcp-option=eno2,17,10.66.192.32:/srv/roach2_boot/root
listen-address=10.66.192.32
dhcp-range=eno2,10.66.192.0,static
bind-interfaces

12. Add the ROACH2 hostname to /etc/hosts by inserting the following lines:
10.66.192.36    He6CRES_roach

13. Restart DHCP service by doing </etc/init.d/dnsmasq restart>

14. Connect a USB cable between a USB slot on a laptop and the FTDI USB port
on the ROACH, then do <minicom> to listen to the ROACH boot output.

15. Connect the ROACH2 to the network on which DHCP is served through
the “PPC NET” port, and push the power button on the ROACH2.

At this point the ROACH2 should try to boot over the network using DHCP
obtained from the server. Verify that this is working by monitoring it through
minicom: the output to expect is detailed in ROACH2_boot_output.txt. It should
show the ROACH2 obtaining an IP address, successfully booting,
and eventually displaying a login prompt. If you wish you can
'login' with username 'root' and no password.

You can also monitor what the server is doing my monitoring various logs, for
example, tail -f /var/log/syslog during the restart.

