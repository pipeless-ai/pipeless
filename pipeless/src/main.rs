use pipeless_ai;
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
        /// Optional. Restart policy for the stream. Either always, never, on_error or on_eos. 'Never' by default.
        #[arg(short, long)]
        restart_policy: Option<String>,
    }
}

#[derive(Subcommand)]
enum RemoveCommand {
    /// Remove a stream by id
    Stream {
        /// Uuid of the stream to delete
        #[arg(long)]
        id: String,
    }
}

#[derive(Subcommand)]
enum UpdateCommand {
    /// Update a stream by id
    Stream {
        /// Uuid of the stream to update
        #[arg(long)]
        id: String,
        /// Optional. New URI where to read the video from. Use "v4l2" to use the device webcam.
        #[arg(short, long)]
        input_uri: Option<String>,
        /// Optional. New URI where to send the output video. Use "screen" to show it directly on the device screen.
        #[arg(short, long)]
        output_uri: Option<String>,
        /// Optional. New comma separated list of stages that will be executed for the frames of the new stream
        #[arg(short, long)]
        frame_path: Option<String>,
        /// Optional. Restart policy for the stream. Either always, never, on_error or on_eos.
        #[arg(short, long)]
        restart_policy: Option<String>,
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
    /// Add configuration resources
    Add {
        #[command(subcommand)]
        command: Option<AddCommand>,
    },
    /// Remove configuration resources
    Remove {
        #[command(subcommand)]
        command: Option<RemoveCommand>,
    },
    /// Update configuration resources
    Update {
        #[command(subcommand)]
        command: Option<UpdateCommand>,
    },
    /// List configuration resources
    List {
        #[command(subcommand)]
        command: Option<ListCommand>,
    },
}

fn main() {
    let cli = Cli::parse();

    match &cli.command {
        Some(Commands::Init { project_name , template}) => pipeless_ai::cli::init::init(&project_name, template),
        Some(Commands::Start { stages_dir }) => pipeless_ai::cli::start::start_pipeless_node(&stages_dir),
        Some(Commands::Add { command }) => {
            match &command {
                Some(AddCommand::Stream { input_uri, output_uri, frame_path , restart_policy}) => pipeless_ai::cli::streams::add(input_uri, output_uri, frame_path, restart_policy),
                None =>  println!("Use --help to see the complete list of available commands"),
            }
        },
        Some(Commands::Remove { command }) => {
            match &command {
                Some(RemoveCommand::Stream { id }) => pipeless_ai::cli::streams::remove(id),
                None =>  println!("Use --help to see the complete list of available commands"),
            }
        },
        Some(Commands::Update { command }) => {
            match &command {
                Some(UpdateCommand::Stream { id, input_uri, output_uri, frame_path , restart_policy}) => pipeless_ai::cli::streams::update(id, input_uri, output_uri, frame_path, restart_policy),
                None =>  println!("Use --help to see the complete list of available commands"),
            }
        },
        Some(Commands::List { command }) => {
            match &command {
                Some(ListCommand::Streams) => pipeless_ai::cli::streams::list(),
                None =>  println!("Use --help to see the complete list of available commands"),
            }
        },
        None => println!("Use --help to see the complete list of available commands"),
    }
}
