## Capture with TSHARK

1. Install tshark

   ```sh
   sudo apt install tshark
   ```

2. List interfaces

   ```sh
   thshark -D
   ```

3. capture interface

   ```sh
   tshark -i enp2s0 -f "host 192.168.1.116" -w capture.pcap
   ```

4. 3

