use pipeless;
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum AddCommand {
    /// Add a new stream
    Stream {
        /// URI where to read the video from. Use "v4l2" to use the device webcam.
        #[arg(short, long)]
        input_uri: String,
        /// Optional. URI where to send the output video. Use "screen" to show it directly on the device screen.
        #[arg(short, long)]
        output_uri: Option<String>,
        /// Comma separated list of stages that will be executed for the frames of the new stream
        #[arg(short, long)]
        frame_path: String,
    }
}

#[derive(Subcommand)]
enum ListCommand {
    /// List current streams
    Streams,
}

#[derive(Subcommand)]
enum Commands {
    /// Init a new Pipeless project
    Init {
        /// New project name
        project_name: String,
        /// Name of the template to scaffold the project
        #[arg(short, long)]
        template: Option<String>,
    },
    /// Start the pipeless node
    Start {
        /// Read stages from the specified directory
        #[arg(short, long)]
        stages_dir: String,
    },
    /// Add resources to the configuration
    Add {
        #[command(subcommand)]
        command: Option<AddCommand>,
    },
    /// List configuration resources
    List {
        #[command(subcommand)]
        command: Option<ListCommand>,
    }
}


fn main() {
    let cli = Cli::parse();

    match &cli.command {
        Some(Commands::Init { project_name , template}) => pipeless::cli::init::init(&project_name, template),
        Some(Commands::Start { stages_dir }) => pipeless::cli::start::start_pipeless_node(&stages_dir),
        Some(Commands::Add { command }) => {
            match &command {
                Some(AddCommand::Stream { input_uri, output_uri, frame_path }) => pipeless::cli::streams::add(input_uri, output_uri, frame_path),
                None =>  println!("Use --help to see the complete list of available commands"),
            }
        },
        Some(Commands::List { command }) => {
            match &command {
                Some(ListCommand::Streams) => pipeless::cli::streams::list(),
                None =>  println!("Use --help to see the complete list of available commands"),
            }
        },
        None => println!("Use --help to see the complete list of available commands"),
    }
}
