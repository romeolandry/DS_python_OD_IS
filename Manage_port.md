# manage Port on Jetson nano 

`rtsp://localhost:8554/ds-test`

- listing open port using `ss`

	sudo ss -tulpn

	- t : all TCP
	- u : All UDP
	- l : Display all listening server socket
	- p :show PIP and name of the program using prot
	- n : don't rsolve names 

- using [ufw](https://www.cyberciti.biz/faq/how-to-setup-a-ufw-firewall-on-ubuntu-18-04-lts-server/)
  
  * if recive this error `ip6tables-restore: line 142 failed` desable ipv6 in to `/etc/default/ufw` 
