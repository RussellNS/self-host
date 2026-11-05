while true; do 
  CONTAINER_ID=$(docker ps -q --filter "name=test")
  if [ ! -z "$CONTAINER_ID" ]; then
    echo "Found test container: $CONTAINER_ID. Fetching logs..."
    docker exec "$CONTAINER_ID" id
    docker logs -f "$CONTAINER_ID"
    docker exec "$CONTAINER_ID" ls -lh /certs/
    docker exec "$CONTAINER_ID" ls -lh /certs/frp/
    break
  fi
  sleep 0.1
done
