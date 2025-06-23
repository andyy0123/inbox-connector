#!/bin/bash

echo "Waiting for MongoDB instances to start..."
sleep 10

echo "Initializing Replica Set..."
mongosh --host mongo1:27017 --username admin --password password --authenticationDatabase admin <<EOF
rs.initiate({
  _id: "rs0",
  version: 1,
  members: [
    { _id: 0, host: "mongo1:27017", priority: 2 },
    { _id: 1, host: "mongo2:27017", priority: 1 },
    { _id: 2, host: "mongo3:27017", priority: 1 }
  ]
});
EOF

echo "Wait for Replica Set election ..."
sleep 15

echo "Checking Replica Set status..."
mongosh --host mongo1:27017 --username admin --password password --authenticationDatabase admin --eval "rs.status()"

echo "Replica Set initialization complete!"