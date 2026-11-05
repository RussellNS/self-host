#!/bin/bash
while true; do
  CONTAINER_ID=$(docker ps -q --filter "name=test")
  if [ ! -z "$CONTAINER_ID" ]; then
    echo "--- Found test container: $CONTAINER_ID ---"

    #  1. Verify who the container is running as
    echo "[DEBUG] Checking user 'id'..."
    docker exec "$CONTAINER_ID" id

    #  2. Verify the certs in the '/certs/' directory
    echo "[DEBUG] Checking '/certs/' directory..."
    docker exec "$CONTAINER_ID" ls -lh /certs/

    #  3. Verify the certs in the '/certs/frp/' directory
    echo "[DEBUG] Checking '/certs/frp/' directory..."
    docker exec "$CONTAINER_ID" ls -lh /certs/frp/

    #  4. Verify Environment Variables
    echo "[DEBUG] Checking environment..."
    docker exec "$CONTAINER_ID" env | grep -E "NEXTCLOUD_URL|APP_ID|HP_"

    #  4. Verify '/etc/hosts'...
    echo "[DEBUG] Checking '/etc/hosts'..."
    docker exec "$CONTAINER_ID" cat /etc/hosts

    #  5. Test DNS/Network Reachability back to Nextcloud
    # Replace 'example.com' if it's internal or use the service name 'web'
    echo "[DEBUG] Testing reachability to Nextcloud..."
    docker exec "$CONTAINER_ID" ping -c 2 example.com

    #  6. Check for the Unix Socket
    # The logs say Uvicorn is running on /tmp/exapp.sock
    echo "[DEBUG] Verifying Uvicorn socket..."
    docker exec "$CONTAINER_ID" ls -la /tmp/exapp.sock

    #  7. Manual local request inside the test container
    # This checks if the ExApp itself is responding via the socket
    echo "[DEBUG] Testing local ExApp response..."
    docker exec "$CONTAINER_ID" curl -s --unix-socket /tmp/exapp.sock http://localhost/heartbeat || echo "Heartbeat failed"

    #  8. Check DNS Resolution
    echo "[DEBUG] Who does the container think example.com is?"
    docker exec "$CONTAINER_ID" getent hosts example.com

    #  9. Trace the Route
    echo "[DEBUG] Tracing path to Nextcloud..."
    # Using 'nc' (netcat) to check if port 443 is even open from the container's perspective
    docker exec "$CONTAINER_ID" sh -c "nc -zv example.com 443" || echo "CANNOT REACH PORT 443"

    # 10. Check MTU Issues (Common with Raspberry Pi / Stream blocks)
    echo "[DEBUG] Checking MTU (should usually be 1500 or 1450)..."
    docker exec "$CONTAINER_ID" ip addr | grep mtu

    # 11. Attempt a Header-only request
    # This checks if Nginx/Nextcloud is rejecting the container's handshake
    echo "[DEBUG] Attempting TLS Handshake to Nextcloud..."
    docker exec "$CONTAINER_ID" curl -vIk https://example.com 2>&1 | grep -E "Connected|SSL|HTTP/"

    # 12. Capture internal socket activity
    echo "[DEBUG] Checking for active listeners inside test container..."
    docker exec "$CONTAINER_ID" netstat -tulpn || docker exec "$CONTAINER_ID" ss -tulpn

    # 13. Check the actual Nextcloud AppAPI endpoint response
    echo "[DEBUG] Testing Nextcloud AppAPI endpoint reachability..."
#    docker exec "$CONTAINER_ID" curl -vIk -H "Content-Type: application/json" "${NEXTCLOUD_URL}/ocs/v2.php/apps/appapi/api/v1/ex-app/heartbeat?format=json"
    docker exec "$CONTAINER_ID" curl -vIk -H "Content-Type: application/json" "https://example.com/ocs/v2.php/apps/appapi/api/v1/ex-app/heartbeat?format=json"

    # 14. Check for 'Harp' backend availability in the HaRP container
    echo "[DEBUG] Checking HaRP's view of the backends..."
    docker exec nextcloud_appapi-harp haproxy -c -f /run/harp/haproxy.cfg

    # 15. Capture logs continuously
    docker logs -f "$CONTAINER_ID"
    break
  fi
  sleep 0.1
done
