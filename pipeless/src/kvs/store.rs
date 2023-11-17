use log::error;
use sled;
use lazy_static::lazy_static;

// We assume the type implementing StoreInterface can be send thread safely
pub trait StoreInterface: Sync {
    fn get(&self, key: &str) -> String;
    fn set(&self, key: &str, value: &str);
}

struct LocalStore {
    backend: sled::Db,
}
impl LocalStore {
    fn new() -> Self {
        let db_path = "/tmp/.pipeless_kv_store";
        let db = sled::open(db_path).expect("Failed to open KV store");
        Self { backend: db }
    }
}
impl StoreInterface for LocalStore {
    /// Insert a KV pair, logs an error if it fails, but do not stop the program.
    /// Trying to get the key will return an empty string.
    fn set(&self, key: &str, value: &str) {
        if let Err(err) = self.backend.insert(key, value) {
            error!("Error inserting key {} with value {} in local KV store. Error: {}", key, value, err);
        }
    }

    /// Returns the value or an empty string
    fn get(&self, key: &str) -> String {
        match self.backend.get(key) {
            Ok(v) => {
                match v.as_deref() {
                    Some(v) => std::str::from_utf8(v).unwrap().into(),
                    None => String::from("")
                }
            },
            Err(err) => {
                error!("Error getting value for key {} from local KV store. Error: {}", key, err);
                String::from("")
            }
        }
    }
}

// TODO: setup Redis or any other distributed solution.
// Important: Note that any type implementing StoreInterface must be thread safe
struct DistributedStore {}
impl DistributedStore {
    fn new() -> Self { unimplemented!() }
}
impl StoreInterface for DistributedStore {
    fn get(&self, key: &str) -> String { unimplemented!() }
    fn set(&self, key: &str, value: &str) { unimplemented!() }
}

lazy_static! {
    // TODO: Add support for distributed store do not hardcode the local one
    pub static ref KV_STORE: Box<dyn StoreInterface> = Box::new(LocalStore::new());
}
