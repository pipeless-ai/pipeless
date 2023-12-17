use std::fmt;
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;
use std::str::FromStr;
use log::{error, warn};
use serde_derive::{Serialize, Deserialize};
use uuid;

// The reconciler takes care of moving streams to the target state
#[derive(Debug,Copy,Clone,Serialize,Deserialize,PartialEq)]
pub enum StreamEntryState {
    Running,
    Completed,
    Error,
}

#[derive(Debug,Clone,Serialize,Deserialize,PartialEq)]
pub struct RestartPolicyError;
impl fmt::Display for RestartPolicyError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Unknown restart policy")
    }
}

#[derive(Debug,Copy,Clone,Serialize,PartialEq)]
pub enum RestartPolicy {
    Never, // Never restart
    Always, // Restart when there is an error or the stream reaches the end
    OnError, // Restart when there is an error
    OnEos, // Restart when the stream reaches the end
}
impl FromStr for RestartPolicy {
    type Err = RestartPolicyError;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "never" | "Never" => Ok(Self::Never),
            "always" | "Always" => Ok(Self::Always),
            "onerror" | "OnError" | "onError" | "Onerror" | "on_error" | "On_Error" => Ok(Self::OnError),
            "oneos" | "OnEos" | "onEos" | "Oneos" | "on_eos" | "On_Eos" => Ok(Self::OnEos),
            _ => Err(RestartPolicyError),
        }
    }
}
impl<'de> serde::Deserialize<'de> for RestartPolicy {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let s: String = serde::Deserialize::deserialize(deserializer)?;

        match s.parse::<RestartPolicy>() {
            Ok(restart_policy) => Ok(restart_policy),
            Err(err) => Err(serde::de::Error::custom(format!("Error parsing restart policy: {}", err))),
        }
    }
}
impl fmt::Display for RestartPolicy {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            RestartPolicy::Never => write!(f, "never"),
            RestartPolicy::Always => write!(f, "always"),
            RestartPolicy::OnError => write!(f, "on_error"),
            RestartPolicy::OnEos => write!(f, "on_eos"),
        }
    }
}

fn calculate_hash<T: Hash>(data: &T) -> u64 {
    let mut hasher = DefaultHasher::new();
    data.hash(&mut hasher);
    hasher.finish()
}

fn calculate_entry_hash(
    input_uri: &str,
    output_uri: Option<&str>,
    frame_path: &Vec<String>,
    restart_policy: &RestartPolicy
) -> u64 {
    let mut hash = calculate_hash(&input_uri);
    if let Some(out_uri) = output_uri {
        // Combine hashs with XOR to avoid overflows
        hash = hash ^ calculate_hash(&out_uri);
    }
    hash = hash ^ calculate_hash(&frame_path.join("/"));
    hash = hash ^ calculate_hash(&restart_policy.to_string());
    hash
}

#[derive(
    Clone,
    Debug,
    PartialEq,
    Serialize,
    Deserialize
)]
pub struct StreamsTableEntry {
    /// Id of the dynamic coniguration entry
    id: uuid::Uuid,
    input_uri: String,
    /// There can be no output
    output_uri: Option<String>,
    frame_path: Vec<String>, // The ordered list of stages
    /// The id of the associated processing pipeline.
    /// Optional because it will be added an removed when streams reach their end
    /// to allow processing several consecutive streams from the same source
    pipeline_id: Option<uuid::Uuid>,
    // To know when the entry (only the URIs) has changed.
    // An entry that does not match the hash will be re-created since it has been updated.
    hash: u64,
    target_state: StreamEntryState,
    restart_policy: RestartPolicy,
}
impl StreamsTableEntry {
    pub fn new(
        input_uri: String,
        output_uri: Option<String>,
        frame_path: Vec<String>,
        restart_policy: RestartPolicy,
    ) -> Self {
        let entry_hash = calculate_entry_hash(&input_uri, output_uri.as_deref(), &frame_path, &restart_policy);
        // We have to use underscores when providing the stage names as modules to some laguages like Python.
        let sanitized_frame_path: Vec<String> = frame_path.iter().map(|s| s.replace("-", "_")).collect();

        let mut restart_policy = restart_policy;
        let using_input_file = input_uri.starts_with("file://");
        let using_output_file = match output_uri.clone() {
            Some(uri) => uri.starts_with("file://"),
            None => false
        };
        if using_input_file || using_output_file {
            if restart_policy != RestartPolicy::Never {
                warn!("Overriding restart policy with 'never' because the stream uses files");
                restart_policy = RestartPolicy::Never;
            }
        }

        Self {
            id: uuid::Uuid::new_v4(),
            input_uri: input_uri.to_string(),
            output_uri: output_uri.map(|x| x.to_string()),
            frame_path: sanitized_frame_path,
            pipeline_id: None, // No pipeline id assigned when created
            hash: entry_hash,
            target_state: StreamEntryState::Running,
            restart_policy,
        }
    }

    pub fn get_id(&self) -> uuid::Uuid {
        self.id
    }

    pub fn get_input_uri(&self) -> &str {
        &self.input_uri
    }
    pub fn set_input_uri(&mut self, new_uri: &str) {
        self.input_uri = new_uri.to_owned()
    }

    pub fn get_output_uri(&self) -> Option<&str> {
        self.output_uri.as_deref()
    }
    pub fn set_output_uri(&mut self, new_uri: Option<String>) {
        self.output_uri = new_uri
    }

    pub fn get_frame_path(&self) -> &Vec<String> {
        &self.frame_path
    }
    pub fn set_frame_path(&mut self, new_path: Vec<String>) {
        self.frame_path = new_path
    }

    pub fn assign_pipeline(&mut self, pipeline_id: uuid::Uuid) {
        self.pipeline_id = Some(pipeline_id);
    }

    pub fn unassign_pipeline(&mut self) {
        self.pipeline_id = None;
    }

    pub fn get_pipeline(&self) -> Option<uuid::Uuid> {
        self.pipeline_id
    }

    /// Returns the hash that the entry has from its creation
    pub fn get_stored_hash(&self) -> u64 {
        self.hash
    }

    /// Calculates the hash that the entry should have according to the current values
    pub fn hash(&self) -> u64 {
        calculate_entry_hash(
            self.get_input_uri(),
            self.get_output_uri(),
            &self.frame_path,
            &self.restart_policy,
        )
    }

    pub fn get_target_state(&self) -> StreamEntryState {
        self.target_state
    }

    pub fn set_target_state(&mut self, state: StreamEntryState) {
        self.target_state = state;
    }

    pub fn set_restart_policy(&mut self, restart_policy: RestartPolicy) {
        self.restart_policy = restart_policy;
    }

    pub fn get_restart_policy(&self) -> RestartPolicy {
        self.restart_policy
    }
}

/// Represents the Pipeless dynamic streams configuration
/// which is modified by the user ahdn automatically handled
pub struct StreamsTable {
    table: Vec<StreamsTableEntry>,
}
impl StreamsTable {
    pub fn new() -> Self {
        Self {
            table: Vec::new(),
        }
    }

    /// Get a copy of the streams table
    pub fn get_table(&self) -> Vec<StreamsTableEntry> {
        self.table.clone()
    }

    pub fn add(&mut self, entry: StreamsTableEntry) -> Result<(), String> {
        if self.table.iter().any(|e| e.input_uri == entry.input_uri) {
            return Err("Duplicated input_uri".to_string());
        }
        if let Some(ref output_uri) = entry.output_uri {
            // When the output is to the screen we allow the duplication
            if output_uri != "screen" && self.table.iter().any(|e| e.output_uri == Some(output_uri.clone())) {
                return Err("Duplicated output_uri".to_string());
            }
        }

        self.table.push(entry);
        Ok(())
    }

    pub fn get_entry_by_id(&self, entry_id: uuid::Uuid) -> Option<&StreamsTableEntry> {
        self.table.iter().find(|entry| entry.get_id() == entry_id)
    }

    pub fn remove(&mut self, stream_id: uuid::Uuid) -> Option<StreamsTableEntry> {
        if let Some(index) = self.table.iter().position(|entry| entry.id == stream_id) {
            let removed_entry = self.table.remove(index);
            Some(removed_entry)
        } else {
            None
        }
    }

    pub fn set_stream_pipeline(&mut self, stream_id: uuid::Uuid, pipeline_id: uuid::Uuid) -> Result<(), String> {
        if self.table.iter().any(|entry| entry.pipeline_id == Some(pipeline_id)) {
            return Err("Pipeline ID already assigned to another entry".to_string());
        }

        if let Some(entry) = self.table.iter_mut().find(|entry| entry.id == stream_id) {
            entry.assign_pipeline(pipeline_id);
            Ok(())
        } else {
            Err("Entry not found".to_string())
        }
    }

    /// Since pipeline_ids are unique we can get an entry by pipeline id
    pub fn get_entry_by_pipeline_id(&mut self, pipeline_id: uuid::Uuid) -> Option<&mut StreamsTableEntry> {
        self.table.iter_mut().find(|entry| entry.pipeline_id == Some(pipeline_id))
    }

    pub fn find_by_pipeline_id(&self, pipeline_id: uuid::Uuid) -> Option<&StreamsTableEntry> {
        self.table.iter().find(|entry| entry.get_pipeline() == Some(pipeline_id))
    }
    pub fn find_by_pipeline_id_mut(&mut self, pipeline_id: uuid::Uuid) -> Option<&mut StreamsTableEntry> {
        self.table.iter_mut().find(|entry| entry.get_pipeline() == Some(pipeline_id))
    }

    pub fn update_by_entry_id(
        &mut self, entry_id: uuid::Uuid, input_uri: &str, output_uri: Option<String>,
        frame_path: Vec<String>, restart_policy: RestartPolicy
    ) {
        if let Some(entry) = self.table.iter_mut().find(|entry| entry.id == entry_id) {
            entry.unassign_pipeline();
            entry.set_input_uri(input_uri);
            entry.set_output_uri(output_uri);
            entry.set_frame_path(frame_path);
            entry.set_restart_policy(restart_policy);
        } else {
            error!("Unable to update stream entry. Stream id not found {}", entry_id);
        }
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_entry_duplicated_input() {
        let mut table = StreamsTable::new();
        let entry1 = StreamsTableEntry::new(
            "input1".to_string(),
            None,
            vec!["s1".to_owned(), "s2".to_owned()],
            RestartPolicy::Never,
        );
        assert!(table.add(entry1).is_ok());
        assert_eq!(table.get_table().len(), 1);

        // Adding an entry with a duplicate input_uri should fail
        let entry2 = StreamsTableEntry::new(
            "input1".to_string(),
            None,
            vec!["s1".to_owned(), "s2".to_owned()],
            RestartPolicy::Never,
        );
        assert!(table.add(entry2).is_err());
    }

    #[test]
    fn test_add_entry_duplicated_output() {
        let mut table = StreamsTable::new();
        let entry1 = StreamsTableEntry::new(
            "input1".to_string(),
            Some("output1".to_string()),
            vec!["s1".to_owned(), "s2".to_owned()],
            RestartPolicy::Never,
        );
        assert!(table.add(entry1).is_ok());
        assert_eq!(table.get_table().len(), 1);

        // Adding an entry with a duplicate output_uri should fail
        let entry2 = StreamsTableEntry::new(
            "input2".to_string(),
            Some("output1".to_string()),
            vec!["s1".to_owned(), "s2".to_owned()],
            RestartPolicy::Never,
        );
        assert!(table.add(entry2).is_err());
    }

    #[test]
    fn test_remove_entry() {
        let mut table = StreamsTable::new();
        let entry1 = StreamsTableEntry::new(
            "input1".to_string(),
            None,
            vec!["s1".to_owned(), "s2".to_owned()],
            RestartPolicy::Never,
        );
        table.add(entry1.clone()).unwrap();

        let removed_entry = table.remove(entry1.get_id())
            .expect("Could not get entry");
        assert_eq!(removed_entry, entry1);
        assert_eq!(table.get_table().len(), 0);

        // Removing a non-existent entry should return None
        assert_eq!(table.remove(uuid::Uuid::new_v4()), None);
    }

    #[test]
    fn test_set_entry_pipeline() {
        let mut table = StreamsTable::new();
        let entry1 = StreamsTableEntry::new(
            "input1".to_string(),
            None,
            vec!["s1".to_owned(), "s2".to_owned()],
            RestartPolicy::Never,
        );
        table.add(entry1.clone()).unwrap();

        let pipeline_id = uuid::Uuid::new_v4();
        assert!(table.set_stream_pipeline(entry1.get_id(), pipeline_id).is_ok());
        assert_eq!(table.get_table()[0].get_pipeline(), Some(pipeline_id));

        // Setting a pipeline ID that is already assigned to another entry should fail
        let entry2 = StreamsTableEntry::new(
            "input2".to_string(),
            None,
            vec!["s1".to_owned(), "s2".to_owned()],
            RestartPolicy::Never,
        );
        table.add(entry2.clone()).unwrap();
        assert!(table.set_stream_pipeline(entry2.get_id(), pipeline_id).is_err());
    }

    #[test]
    fn test_find_by_pipeline_id() {
        let mut table = StreamsTable::new();
        let pipeline_id = uuid::Uuid::new_v4();
        let mut entry1 = StreamsTableEntry::new(
            "input1".to_string(),
            Some("output1".to_string()),
            vec!["s1".to_owned(), "s2".to_owned()],
            RestartPolicy::Never,
        );
        entry1.assign_pipeline(pipeline_id);
        table.add(entry1.clone()).unwrap();

        // Finding an entry by its pipeline ID
        let found_entry = table.find_by_pipeline_id(pipeline_id);
        assert_eq!(found_entry, Some(&entry1));

        // Finding an entry by a non-existent pipeline ID
        let non_existent_pipeline_id = uuid::Uuid::new_v4();
        let not_found_entry = table.find_by_pipeline_id(non_existent_pipeline_id);
        assert_eq!(not_found_entry, None);
    }
}
