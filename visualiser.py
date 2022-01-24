
from Parser.jsonParser import parse_json
from Parser.yamlParser import parse_yaml

from bokeh.io import output_file, show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure, show
from bokeh.transform import jitter


class visualiser:
    
    def __init__(self, yaml_filepath, json_filepath):
        
        yaml = parse_yaml(yaml_filepath)
        json = parse_json(json_filepath)
        
        self.graph_name = yaml_filepath.split(".")[0] + "_Trace"
        
        # [reactor.name0, reactor.name1, ...]
        self.y_axis_labels = json.y_axis_labels
        
        # {reactor.name0 : 0, reactor.name1 : 1, ...}
        self.reactor_number = json.reactor_number

        # reversal of reactor_number
        self.number_label = json.number_label

        yaml_data = yaml.reaction_dict
        # {reactor : {reaction : {attribute : value}}}
        
        json_data = json.data
        # {reactor: {reaction: [list of executions of reactions]}}
        
        
        # Dictionary containing all compiled data for each instantaneous event execution 
        # Note: time_start is used for the x-axis, y-axis is the y value which is later substituted for a reaction name
        self.ordered_inst_events_dict = {"name": [], "reactor": [], "reaction": [], "time_start": [], "time_end": [], 
                                         "trace_event_type": [], "priority": [], "level": [], "triggers": [], "effects": [], "y_axis": []}
        
        # Dictionary containing all compiled data for each execution event execution
        # x_multi_line and y_multi_line contain nested lists with start and end x and y values respectively. These are used to draw the multilines
        self.ordered_exe_events_dict = {"name": [], "time_start": [], "time_end": [], "trace_event_type": [], "priority": [], 
                                        "level": [], "triggers": [], "effects": [], "x_multi_line": [], "y_multi_line": [], "y_axis": []}

        
        # Iterate through all recorded reactions and order into dicts
        for reactor, reactions in json_data.items():
            
            # Execution events (not instantaneous)
            if reactor == "Execution":
                for reaction in reactions:
                    execution_events_iter = iter(json_data[reactor][reaction])
                    for reaction_instance in execution_events_iter:
                    
                        # JSON Data
                        self.ordered_exe_events_dict["name"].append(reaction_instance["name"])
                        self.ordered_exe_events_dict["time_start"].append(reaction_instance["ts"])
                        
                        # x - main reactor name
                        # y - reactor name                      E.g. ReflexGame.g.reaction1
                        # z - reaction name
                        x,y,z = reaction_instance["name"].split(".", 2)
                        
                        current_reactor_name = x + "." + y
                        current_reaction_name = z
                        
                        self.ordered_exe_events_dict["y_axis"].append(
                            self.reactor_number[reaction_instance["name"]])
                        
                        current_reaction = yaml_data[current_reactor_name][current_reaction_name]
                        
                        self.ordered_exe_events_dict["trace_event_type"].append("execution")
                            
                        # YAML Data
                        attribute_list = ["priority", "level", "triggers", "effects"]
                        for attribute in attribute_list:
                            if attribute in current_reaction:
                                self.ordered_exe_events_dict[attribute].append(
                                    current_reaction[attribute])
                            else:
                                self.ordered_exe_events_dict[attribute].append(
                                    "n.a.")
                        
                        # Get end time of event by going to the next json event (start and end events are distinct)
                        try:
                            next_reaction = next(execution_events_iter)
                            self.ordered_exe_events_dict["time_end"].append(
                                next_reaction["ts"])
                        
                        # If no end event exists, add end time as same timestamp (i.e. the last element of time_start)
                        except StopIteration as e:
                            self.ordered_exe_events_dict["time_end"].append(
                                self.ordered_exe_events_dict["time_start"][-1])
                    
            # All other events from the trace 
            else:
                for reaction in reactions:
                    for reaction_instance in json_data[reactor][reaction]:
                        
                        # JSON Data
                        self.ordered_inst_events_dict["name"].append(
                            reactor + "." + reaction)
                        self.ordered_inst_events_dict["reactor"].append(reactor)
                        self.ordered_inst_events_dict["reaction"].append(reaction)
                        self.ordered_inst_events_dict["time_start"].append(
                            reaction_instance["ts"])
                        self.ordered_inst_events_dict["time_end"].append(
                            reaction_instance["ts"])
                        self.ordered_inst_events_dict["trace_event_type"].append(
                            "instant")
                        self.ordered_inst_events_dict["y_axis"].append(
                            self.reactor_number[reactor + "." + reaction])
                        
                        # YAML Data
                        current_reaction = yaml_data[reactor][reaction]
                        
                        attribute_list = ["priority", "level", "triggers", "effects"]
                        for attribute in attribute_list:
                            if attribute in current_reaction:
                                self.ordered_inst_events_dict[attribute].append(
                                    current_reaction[attribute])
                            else:
                                self.ordered_inst_events_dict[attribute].append("n.a.")
        
    
    
    
    def build_graph(self):
        """Builds the bokeh graph"""

        # Output to 
        output_file(self.graph_name + ".html")
        
        # Define tooltips
        TOOLTIPS = [
            ("name", "@name"),
            ("time_start", "@time_start"),
            ("time_end", "@time_end"),
            ("trace_event_type", "@trace_event_type"),
            ("priority", "@priority"),
            ("level", "@level"),
            ("triggers", "@triggers"),
            ("effects", "@effects"),
        ]

        # Define figure
        p = figure(sizing_mode="stretch_both",
                   title=self.graph_name)
        
        
        
        # -------------------------------------------------------------------
        # All execution events
        
        # order data for multiline graph
        for start_time, end_time in zip(self.ordered_exe_events_dict["time_start"], self.ordered_exe_events_dict["time_end"]):
            self.ordered_exe_events_dict["x_multi_line"].append(
                [start_time, end_time])

        for y_value in self.ordered_exe_events_dict["y_axis"]:
            self.ordered_exe_events_dict["y_multi_line"].append(
                [y_value, y_value])

        
        # data source
        source_exec_events = ColumnDataSource(
            self.ordered_exe_events_dict)
        
            
        # https://docs.bokeh.org/en/latest/docs/user_guide/plotting.html#line-glyphs

        exe_line = p.multi_line(xs='x_multi_line', ys='y_multi_line', width=12, color="mediumseagreen", hover_alpha=0.5,
                    source=source_exec_events, legend_label="Execution Events", muted_alpha=0.2)

        # -------------------------------------------------------------------      
        
        # Execution event markers 
        exe_x_marker = [((x1 + x2)/2) for x1, x2 in self.ordered_exe_events_dict["x_multi_line"]] 
        exe_y_marker = self.ordered_exe_events_dict["y_axis"]
        
        exe_marker = p.diamond(exe_x_marker, exe_y_marker, color="mediumspringgreen",
                    size = 10, legend_label = "Execution Event Markers", muted_alpha = 0.2)
        
        # -------------------------------------------------------------------
        
        # All instantaneous events
        source_inst_events = ColumnDataSource(self.ordered_inst_events_dict)

        inst_hex = p.hex(x='time_start', y=jitter('y_axis', width=0, mean=0.25), fill_color="hotpink",
                         size=10, source=source_inst_events, legend_label="Instantaneous Events", muted_alpha=0.2)

        # -------------------------------------------------------------------

        p.legend.location = "top_left"

        # Toggle to hide/show events
        p.legend.click_policy = "mute"
        
        # Rename Axes
        p.yaxis.ticker = [y for y in range(len(self.y_axis_labels))]
        p.yaxis.major_label_overrides = self.number_label

        # background
        p.background_fill_color = "beige"
        p.background_fill_alpha = 0.5
        
        # Hover tool only for instantaneous events and execution event lines (so that markers for exe events dont also have a tooltip)
        hover_tool = HoverTool(tooltips=TOOLTIPS, renderers=[
                               inst_hex, exe_line])
        p.add_tools(hover_tool)
        
                
        show(p)




if(__name__ == "__main__"):
    vis = visualiser("yaml_files/ReflexGame.yaml",
                     "traces/reflextrace_formatted.json")

    vis.build_graph()
