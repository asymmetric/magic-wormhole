# To use the web() option, you should do:
# * cd misc
# * npm install vis zepto

from __future__ import print_function
import os, sys, time, json


streams = sys.argv[1:]
num_streams = len(streams)
labels = dict([(num, " "*num + "[%d]" % (num+1) + " "*(num_streams-1-num))
               for num in range(num_streams)])
timeline = []
groups_out = []
group_fns = {}
for which,fn in enumerate(streams):
    group_fns[which] = fn
    with open(fn, "rb") as f:
        for (start, sent, finish, what, start_d, finish_d) in json.load(f):
            timeline.append( (start, sent, finish, which, what,
                              start_d, finish_d) )
    print("%s is %s" % (labels[which], fn))
    groups_out.append({"id": "%d" % which, "content": fn,
                       "className": "group-%d" % which})


timeline.sort(key=lambda row: row[0])
first = timeline[0][0]
print("started at %s" % time.ctime(start))
viz_out = []
server_groups = set()

for num, (start, sent, finish, which, what,
          start_d, finish_d) in enumerate(timeline):
    delta = start - first
    delta_s = "%.6f" % delta
    start_d_str = ", ".join(["%s=%s" % (name, start_d[name])
                             for name in sorted(start_d)])
    finish_d_str = ", ".join(["%s=%s" % (name, finish_d[name])
                              for name in sorted(finish_d)])
    details_str = start_d_str
    if finish_d_str:
        details_str += "/" + finish_d_str
    finish_str = ""
    if finish is not None:
        finish_str = " +%.6f" % (finish - start)
    print("%9s: %s %s %s%s" % (delta_s, labels[which], what, details_str,
                               finish_str))
    viz_start = start*1000
    viz_end = None if finish is None else finish*1000
    viz_type = "range" if finish else "point"
    if what == "wormhole started" or what == "wormhole":
        viz_type = "background"
    viz_content = '<span title="%s">%s</span>' % (details_str or "(No details)",
                                                  what) # sigh
    viz_className = "item-group-%d" % which
    if "waiting" in start_d:
        viz_className += " wait-%s" % start_d["waiting"]
    subgroup = 0
    if what.startswith("get ") or what == "list":
        subgroup = 1
    elif what.startswith("send "):
        subgroup = 2
    elif what == "API get data" or what == "API send data":
        subgroup = 3
    item = {"id": num, "start": viz_start, "end": viz_end,
            "group": "%d" % which, #"subgroup": subgroup,
            "content": viz_content,
            "className": viz_className, # or style:
            "type": viz_type,
            }
    sent_item = None
    if sent is not None:
        server_group = "%d-server" %  which
        sent_item = {"id": "%d.sent" % num, "start": sent*1000,
                     "group": server_group,
                     "content": "",
                     "className": viz_className,
                     "type": "point"}
        server_groups.add((which, server_group))
    viz_out.append(item)
    if sent_item:
        viz_out.append(sent_item)
for (which,group) in server_groups:
    groups_out.append({"id": group, "content": "server %s" % group_fns[which]})
groups_out.sort(key=lambda g: g["id"])

here = os.path.dirname(__file__)
web_root = os.path.join(here, "web")
vis_root = os.path.join(here, "node_modules", "vis", "dist")
zepto_root = os.path.join(here, "node_modules", "zepto")
if not os.path.isdir(vis_root) or not os.path.isdir(zepto_root):
    print("Cannot find 'vis' and 'zepto' in misc/node_modules/")
    print("Please run 'npm install vis zepto' from the misc/ directory.")
    sys.exit(1)

def web():
    # set up a server that serves web/ at the root, plus a /data.json built
    # from {timeline}. Quit when it fetches /done .
    from twisted.web import resource, static, server
    from twisted.internet import reactor, endpoints
    ep = endpoints.serverFromString(reactor, "tcp:8066:interface=127.0.0.1")
    root = static.File(web_root)
    data_json = {"items": viz_out, "groups": groups_out}
    data = json.dumps(data_json).encode("utf-8")
    root.putChild("data.json", static.Data(data, "application/json"))
    root.putChild("vis", static.File(vis_root))
    root.putChild("zepto", static.File(zepto_root))
    class Shutdown(resource.Resource):
        def render_GET(self, request):
            print("timeline ready, server shutting down")
            reactor.stop()
            return "shutting down"
    root.putChild("done", Shutdown())
    site = server.Site(root)
    ep.listen(site)
    import webbrowser
    def launch_browser():
        webbrowser.open("http://localhost:%d/timeline.html" % 8066)
        print("browser opened, waiting for shutdown")
    reactor.callLater(0, launch_browser)
    reactor.run()
web()

