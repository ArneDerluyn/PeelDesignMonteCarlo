import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


n_sims = 10000

pallet_size = 40
uses = 120
hourly_rate = 40
years= 10
PRICE_PEELCOATING = 2.3375

class Case:
    """
    Cost model for peeldesign case

    Attributes:
        purchase (float): Initial purchase cost
        storage (float): monthly storage cost, is divided by pallet size
        storage_months(int): standard 12
        coating_cost = cost of coating application (external)
        peelcoating_cost = cost per unit of peelcoating material
        transport_cost (float): cost for transport, is divided by pallet size


    """

    def __init__(self, name,
                 #purchase=190,
                 storage = 5,
                 storage_months=12,
                 coating_cost = 10,
                 peelcoating_price=2.3375,
                 peelcoating_time=20,
                 coating_internal=False,
                 transport_cost = 85,
                 transport_amount = 0,
                 decoating_time = 10,
                 max_uses=120,
                 #powder=False
                 ):

        self.name = name

        #self.purchase = purchase

        self.storage = storage/pallet_size
        self.storage_months = storage_months
        self.transport_cost = transport_cost/pallet_size
        self.transport_amount = transport_amount
        
        self.coating_cost = coating_cost
        self.peelcoating_price=peelcoating_price
        self.coating_internal=coating_internal
        self.peelcoating_time=peelcoating_time
        self.decoating_time = decoating_time


        self.max_uses = max_uses

    def calc_cost_per_loop(self,
        storage = None,
        transport_cost = None,
        coating_cost = None,
        peelcoating_time = None,
        decoating_time = None,
        peelcoating_price = None,
                  ):

        # Use simulated values if provided, otherwise fall back to object defaults
        storage = self.storage if storage is None else storage / pallet_size
        transport_cost = self.transport_cost if transport_cost is None else transport_cost / pallet_size
        coating_cost = self.coating_cost if coating_cost is None else coating_cost
        peelcoating_time = self.peelcoating_time if peelcoating_time is None else peelcoating_time
        decoating_time = self.decoating_time if decoating_time is None else decoating_time
        peelcoating_price = self.peelcoating_price if peelcoating_price is None else peelcoating_price


        price = 0

        storage_total = storage * self.storage_months

        transport_total = transport_cost * self.transport_amount

        if self.coating_internal:
            coating_cost_total = peelcoating_price + (peelcoating_time / 60) * hourly_rate
        else:
            coating_cost_total = coating_cost

        decoating_total = (decoating_time / 60) * hourly_rate

        price = storage_total + transport_total + coating_cost_total + decoating_total

        #print(storage_total, transport_total, coating_cost_total, decoating_total)


        return price


a = Case("A", storage=0, storage_months=0, transport_cost=0, transport_amount=0, coating_internal=True) #Recoating in shop
d = Case("D", storage_months=3, transport_amount=2, coating_internal=True, peelcoating_price=2.3375) #Shopfitting as a service, coating internal
e = Case("E", storage_months=2,  transport_amount=3, coating_internal=False) #Shopfitting as a service, coating external



print(f'{a.calc_cost_per_loop()}')
print(f'{d.calc_cost_per_loop()}')
print(f'{e.calc_cost_per_loop()}')


cases = [a, d, e]

def sample_pert(minimum, mode, maximum, lamb=4):
    alpha = 1 + lamb * (mode - minimum) / (maximum - minimum)
    beta = 1 + lamb * (maximum - mode) / (maximum - minimum)
    return minimum + np.random.beta(alpha, beta) * (maximum - minimum)

def sample_peelcoating():
    if np.random.rand() < 0.95:
        return np.random.triangular(1.5, 2.33, 2.8)
    else:
        return np.random.triangular(1, 3, 15)

def sample_uses():
    if np.random.rand() < 0.95:
        return 120
    else:
        return np.random.triangular(6, 60, 120)

def sample_inputs():

    #Sample one scenario of uncertain inputs.
    #Adjust these distributions to match your business assumptions.

    return {
        "storage": np.random.normal(5, 2),                 # around 5
        "transport_cost": np.random.normal(85, 25),       # around 85
        "coating_cost": np.random.uniform(9,14),        # low to high
        "decoating_time": np.random.triangular(5, 10, 20),   # centered on 10           
        "peelcoating_price": np.random.triangular(PRICE_PEELCOATING/2, PRICE_PEELCOATING, PRICE_PEELCOATING*2),   # example range
        "peelcoating_time": np.random.triangular(10, 20, 30),   # centered on 20
    }


results = []

for sim in range(n_sims):
    sampled = sample_inputs()

    row = {
        "sim": sim + 1,
        "storage": sampled["storage"],
        "transport_cost": sampled["transport_cost"],
        "coating_cost": sampled["coating_cost"],
        "decoating_time": sampled["decoating_time"],
        "peelcoating_price": sampled["peelcoating_price"],
        "peelcoating_time": sampled["peelcoating_time"],
    }

    for case in cases:


        row[case.name] = case.calc_cost_per_loop(
            storage=sampled["storage"],
            transport_cost=sampled["transport_cost"],
            coating_cost=sampled["coating_cost"],
            decoating_time=sampled["decoating_time"],
            peelcoating_price=sampled["peelcoating_price"],
            peelcoating_time=sampled["peelcoating_time"],
        )

    results.append(row)

df = pd.DataFrame(results)

first10 = df.iloc[:10].copy()
mean_row = df.mean().to_frame().T
mean_row.index = ["Average"]
print(pd.concat([first10, mean_row]))
print()
print("Average cost per case:")
print(df[["A", "D", "E"]].mean())

winner = df[["A", "D", "E"]].idxmin(axis=1)
print()
print("Probability each case is cheapest:")
print(winner.value_counts(normalize=True).sort_index())

print(df[["A","D","E"]].describe())


corr = df.corr(numeric_only=True)

inputs = ["storage","transport_cost","coating_cost","decoating_time","peelcoating_price", "peelcoating_time"]
for case in ["A","D","E"]:
    print(f"\n--- {case} ---")
    print(df[inputs + [case]].corr()[case].drop(case).sort_values(ascending=False))


