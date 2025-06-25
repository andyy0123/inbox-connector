db = db.getSiblingDB('admin');

db.auth('admin', 'password');

db = db.getSiblingDB('inbox_connector_db');

try {
    db.createUser({
        user: 'app_user',
        pwd: 'app_password',
        roles: [
            {
                role: 'readWrite',
                db: 'inbox_connector_db'
            }
        ]
    });
    print('Application user created successfully');
} catch (e) {
    print('User might already exist: ' + e);
}

print('MongoDB initialization completed');