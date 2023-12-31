use glib::BoolError;
use gstreamer as gst;
use log::{error, warn, debug};

pub fn create_generic_component(ctype: &str, cname: &str) -> Result<gst::Element, BoolError> {
    let component = gst::ElementFactory::make(ctype)
        .name(cname)
        .build().or_else(|err| {
            debug!("Failed to create component {} of type {}", cname, ctype);
            Err(err)
        });

    component
}

pub fn format_state(state: gst::State) -> &'static str {
    match state {
        gst::State::VoidPending => "VoidPending",
        gst::State::Null => "Null",
        gst::State::Ready => "Ready",
        gst::State::Paused => "Paused",
        gst::State::Playing => "Playing",
    }
}

pub fn i32_from_caps_structure(structure: &gst::structure::StructureRef, name: &str) -> Result<i32, gst::FlowError> {
    return match structure.value(name) {
        Ok(v) => match v.get::<i32>() {
            Ok(i) => Ok(i),
            Err(_err) => {
                error!("Unable to get {} value", name);
                Err(gst::FlowError::Error)
            }
        },
        Err(_err) => {
            error!("Unable to get {} from caps structure", name);
            Err(gst::FlowError::Error)
        }
    };
}

pub fn fraction_from_caps_structure(
    structure: &gst::structure::StructureRef,
    name: &str
) -> Result<(i32, i32), gst::FlowError> {
    return match structure.get::<gst::Fraction>(name) {
        Ok(f) => Ok((f.numer(), f.denom())),
        Err(_err) => {
            error!("Unable to get {}", name);
            Err(gst::FlowError::Error)
        }
    };
}

pub fn tag_list_to_string(tag_list: &gst::TagList) -> String {
    let mut formatted_tags: Vec<String> = Vec::new();

    for idx in 0..tag_list.n_tags() {
        if let Some(tag_name) = tag_list.nth_tag_name(idx) {
            if tag_name == "taglist" {
                continue;
            }

            let n_tag_values = tag_list.size_by_name(tag_name);

            if n_tag_values == 1 {
                if let Some(tag_value) = tag_list.index_generic(tag_name, 0) {
                    match tag_value.get::<gst::DateTime>() {
                        Ok(datetime) => {
                            let datetime_tag_res = datetime.to_iso8601_string();
                            if let Ok(tag_value) = datetime_tag_res {
                                formatted_tags.push(format!("{}={}", tag_name, tag_value))
                            } else {
                                warn!("Unable to get ISO string from tag");
                            }
                        }
                        Err(_) => formatted_tags.push(format!("{}={:?}", tag_name, tag_value))
                    }
                }
            } else {
                let formatted_values: Vec<String> = (0..n_tag_values)
                    .filter_map(|i| {
                        tag_list.index_generic(tag_name, i).map(|tag_value|  {
                            match tag_value.get::<gst::DateTime>() {
                                Ok(datetime) => {
                                    let datetime_tag_res = datetime.to_iso8601_string();
                                    if let Ok(tag_value) = datetime_tag_res {
                                       tag_value.to_string()
                                    } else {
                                        warn!("Unable to get ISO string from tag");
                                        String::from("")
                                    }
                                }
                                Err(_) => format!("{:?}", tag_value)
                            }
                        })
                    })
                    .collect();
                formatted_tags.push(format!("{}={}", tag_name, formatted_values.join(",")));
            }
        }
    }

    formatted_tags.join(", ")
}
