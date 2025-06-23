use('m365_connector');

db.createUser({
  user: 'app_user',
  pwd: 'app_password',
  roles: [
    {
      role: 'readWrite',
      db: 'm365_connector'
    }
  ]
});

print('MongoDB initialization complete!');