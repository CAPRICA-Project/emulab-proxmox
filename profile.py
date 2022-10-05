"""This profile creates a Proxmox cluster with a default, non routed, VM bridge."""

from geni import portal
from geni.rspec import pg

IMAGE='urn:publicid:IDN+emulab.net+image+Caprica-VZ:pve-7.2'
COMMAND='sudo /local/repository/{} >> /tmp/deploy.stdout 2>> /tmp/deploy.stderr'

def command(cmd):
    """
    Create an execution service
    :param cmd: The command to run
    """
    return pg.Execute(shell='bash', command=COMMAND.format(cmd))

# Create a portal context, needed to defined parameters
pc = portal.Context()

# Create a Request object to start building the RSpec
request = pc.makeRequestRSpec()

# Variable number of nodes
pc.defineParameter('node_count', 'Number of Nodes', portal.ParameterType.INTEGER, 3,
                   longDescription='The number of nodes in the Proxmox cluster')

# Root password
pc.defineParameter('root_password', 'Root password', portal.ParameterType.STRING, 'password',
                   longDescription='The root password used for cluster configuration and login')

# Cluster name
pc.defineParameter('cluster_name', 'Cluster name', portal.ParameterType.STRING, 'pve-cluster',
                   longDescription='The cluster name shown in the Proxmox interface')

# Optional physical type for all nodes
pc.defineParameter('phys_type', 'Optional physical node type', portal.ParameterType.STRING, '',
                   longDescription='Specify a physical node type (pc3000,d710,etc) ' +
                   'instead of letting the resource mapper choose for you.')

# Optional link speed, normally the resource mapper will choose for you based on node availability
pc.defineParameter('link_speed', 'Link Speed', portal.ParameterType.INTEGER, 0,
                   [(0, 'Any'), (100000, '100Mb/s'), (1000000, '1Gb/s'), (10000000, '10Gb/s'),
                    (25000000, '25Gb/s'), (100000000, '100Gb/s')], advanced=True,
                   longDescription='A specific link speed to use for your LAN. Normally, the '
                                   'resource mapper will choose for you based on node availability '
                                   'and the optional physical type.')

# For very large LANs, you might tell the resource mapper to override the bandwidth constraints and
# treat it as "best-effort"
pc.defineParameter('best_effort', 'Best Effort', portal.ParameterType.BOOLEAN, False, advanced=True,
                   longDescription='For very large LANs, you might get an error saying "not '
                                   'enough bandwidth". This options tells the resource mapper to '
                                   'ignore bandwidth and assume you know what you are doing.')

# Sometimes, you want all of your nodes on the same switch. Note that this option can make it
# impossible for your experiment to map.
pc.defineParameter('same_switch', 'No Interswitch Links', portal.ParameterType.BOOLEAN, False,
                   advanced=True,
                   longDescription='Sometimes, you want all the nodes connected to the same '
                                   'switch. This option will ask the resource mapper to do that, '
                                   'although it might make it impossible to find a solution. Do '
                                   'not use this unless you are sure you need it!')

# Optional ephemeral blockstore
pc.defineParameter('temp_fs_size', 'Temporary Filesystem Size', portal.ParameterType.INTEGER,
                   0, advanced=True,
                   longDescription='The size in GB of a temporary file system to mount on each of '
                                   'your nodes. Temporary means that it is deleted when your '
                                   'experiment is terminated. The images provided by the system '
                                   'have small root partitions, so use this option if you expect '
                                   'you will need more space to build your software packages or '
                                   'store temporary files.')

# Instead of a size, ask for all available space
pc.defineParameter('temp_fs_max', 'Temp Filesystem Max Space', portal.ParameterType.BOOLEAN,
                   False, advanced=True,
                   longDescription='Instead of specifying a size for your temporary filesystem, '
                                   'check this box to allocate all available disk space. Leave the '
                                   'size above to zero.')

pc.defineParameter('temp_fs_mount', 'Temporary Filesystem Mount Point',
                   portal.ParameterType.STRING, '/mydata', advanced=True,
                   longDescription='Mount the temporary file system at this mount point')

# Retrieve the values the user specifies during instantiation
params = pc.bindParameters()

# Check parameter validity
if params.node_count < 1:
    pc.reportError(portal.ParameterError('You must choose at least 1 node.', ['node_count']))

if not params.root_password:
    pc.reportError(portal.ParameterError('You must choose a non-empty password', ['root_password']))

if not params.cluster_name:
    pc.reportError(portal.ParameterError('You must choose a non-empty cluster name',
                                         ['cluster_name']))

if params.temp_fs_size < 0 or params.temp_fs_size > 200:
    pc.reportError(portal.ParameterError('Please specify a size greater than zero and lower than '
                                         '200GB', ['temp_fs_size']))

pc.verifyParameters()

# Create the LAN
lan = request.LAN()
if params.best_effort:
    lan.best_effort = True
elif params.link_speed > 0:
    lan.bandwidth = params.link_speed
if params.same_switch:
    lan.setNoInterSwitchLinks()

# Process nodes, adding to link or lan.
for i in range(params.node_count):
    # Create a node and add it to the request
    name = 'node{}'.format(i)
    node = request.RawPC(name)
    node.disk_image = IMAGE
    # Add to the LAN
    iface = node.addInterface('eth1')
    lan.addInterface(iface)
    if i:
        node.addService(command('deploy-others.sh {}'.format(params.root_password)))
    else:
        node.addService(command('deploy-first.sh {} {}'
                                .format(params.root_password, params.cluster_name)))
    # Optional hardware type
    if params.phys_type:
        node.hardware_type = params.phys_type
    # Optional Blockstore
    if params.temp_fs_size > 0 or params.temp_fs_max:
        bs = node.Blockstore(name + '-bs', params.temp_fs_mount)
        if params.temp_fs_max:
            bs.size = '0GB'
        else:
            bs.size = '{}GB'.format(params.temp_fs_size)
        bs.placement = 'any'

# Print the RSpec to the enclosing page.
pc.printRequestRSpec(request)
