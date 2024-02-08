pub enum Language {
    Python,
    Rust,
    Json,
    Wasm,
}
pub struct LanguageDef {
    language: Language,
    extension: String,
}
impl LanguageDef {
    pub fn new(language: Language, extension: &str) -> Self {
        Self { language, extension: String::from(extension) }
    }
    pub fn get_language(&self) -> &Language { &self.language }
    pub fn get_extension(&self) -> &String { &self.extension }
}

pub fn get_available_languages() -> Vec<LanguageDef> {
    vec![
        LanguageDef::new(Language::Python, "py"),
        LanguageDef::new(Language::Rust, "rs"),
        LanguageDef::new(Language::Json, "json"),
        LanguageDef::new(Language::Wasm, "wasm"), // Wasm based hooks are pre-compiled wasm components
    ]
}
