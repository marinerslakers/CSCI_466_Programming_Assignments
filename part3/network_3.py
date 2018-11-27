import queue
import threading
import json


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)
    
    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)
            
        
## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths 
    dst_S_length = 5
    prot_S_length = 1
    
    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S
        
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += self.data_S
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0 : NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length : NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise('%s: unknown prot_S field: %s' %(self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length : ]        
        return self(dst, prot_S, data_S)
    

    

## Implements a network host for receiving and transmitting data
class Host:
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return self.addr
       
    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out') #send packets always enqueued successfully
        
    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))
       
    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router
class Router:
    
    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        #save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D    # {neighbor: {interface: cost}}


        self.rt_tbl_D = {}      # {destination: {router: cost}}
        for i in cost_D.keys():    #for each neighbor inside the dictionary
            for k in cost_D[i].keys(): #for each interface 
                self.rt_tbl_D.update({i: {self.name: cost_D[i][k]}}) #updates the new table with the cost to that neighbor

        self.rt_tbl_D.update({str(self): {str(self): 0}})
        print('%s: Initialized routing table' % self)
        self.print_routes()
    
        
    ## Print routing table
    def print_routes(self):
        print('---------------------')
        h = "| " + str(self) + " | " #prints in the top left corner the router the call was made from(who owns the routing table)
        route = [] #where its heading
        for i in self.rt_tbl_D.keys(): #for each destination inside the routing table(should equal the whole network)
            h = h + i + " | " #add the destination to the header(makes the first row)
            for k in self.rt_tbl_D[i].keys(): #for every router in the list
                if k not in route: #while going through them, if they arent present add it to our route
                    route.append(k)
        print(h) #prints the first row with the header for the network
        for n in route: #go through all the routes
            row = "| " + n + " | " #print the name
            for j in self.rt_tbl_D.keys(): #prints the costs to get to a certain location, 
                if self.rt_tbl_D[j][n] > 9: #if statements are just for formatting a little better
                    row = row + str(self.rt_tbl_D[j][n]) + "| "
                else: #checks 10 or bigger for 1 space, or 2 spaces for smaller
                    row = row + str(self.rt_tbl_D[j][n]) + "  | "
            print(row)
        print("")


    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and 
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            #get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            #if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))
            

    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, s):
        try:
            short = 2000 #larger than anything we will be using
            path = 22 #meaningless interface used(will be changed throughout to best one)
            for i in self.rt_tbl_D[p.dst]: #check each router
                if i == self.name: #skip if its ours
                    continue #skip
                route_cost = self.rt_tbl_D[p.dst][i] #Pulls the cost for that router from the routing table
                if short > route_cost: #if our shortest is bigger than the current route we are looking at(initial will go to first router)
                    short = route_cost #set shortest to this one
                    for k in self.cost_D[i]: #the interface to get to that router
                        path = k #sets that as the path to be used
            for i in self.cost_D: # checks the neighbors
                if p.dst == i: #if neighbor is the destination, then we set our path to that interface for the neighbor
                    for k in self.cost_D[i]:
                        path = k
            self.intf_L[1].put(p.to_byte_S(), 'out', True)
            #given code below
            print('%s: forwarding packet "%s" from interface %d to %d' % (self, p, s, 1))
        except queue.Full: #just circling around a set instead of being routed out, breaks the system
            print('%s: packet "%s" lost on interface %d' % (self, p, s))
            pass


    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        d = {} #create an empty dictionary
        for j in self.rt_tbl_D: #for every destination in the routing table
            d[j] = {} #empty dictionary created for that destination
            d[j][self.name] = self.rt_tbl_D[j][self.name] 
        dictString = json.dumps(d) #turns a dictionary to a string
        p = NetworkPacket(0, 'control', dictString) #send it off to make a packet
        try: #given code
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full: #given code
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        print('%s: Received routing update %s from interface %d' % (self, p, i))
        d = json.loads(p.data_S) #turn it back into a dictionary
        update = False #whether or not the table needs to be updated, set to false initially and only flips when change is needed
        for i in d.keys(): #for each destination in the dictionary
            for k in d[i]: #the router that was sent
                if i not in self.rt_tbl_D: #if the destination isnt a part of your table, add it
                    self.rt_tbl_D[i] = {}
                self.rt_tbl_D[i][k] = d[i][k]
        for i in self.rt_tbl_D: #for each destination in the routing table(been updated already to have all of them)
            if i == self.name: # if our destination is us, skip out of the below stuff
                continue
            min = 100 
            if self.name in self.rt_tbl_D[i]: #if the current router has a link to the destination, its the shortest path
                min = self.rt_tbl_D[i][self.name]
            for k in self.rt_tbl_D[i]: 
                if k == self.name: #if we are the route, our cost is our cost
                    cost = self.rt_tbl_D[i][k]
                else: #otherwise its our cost plus the additional routing cost
                    cost = self.rt_tbl_D[i][k] + self.rt_tbl_D[k][self.name]
                if cost < min: #if this cost is better than the smallest so far, then it is our new minimum and we need to update
                    update = True
                    min = cost
            self.rt_tbl_D[i][self.name] = min #set the cost to what the minimum we found was
        if update: #if we need to update, we send off the new costs to all connected routers
            for i in self.cost_D.keys():
                for k in self.cost_D[i]:
                    self.send_routes(k)
                    
                
                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 
