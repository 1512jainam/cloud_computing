import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import math
import random
import itertools
from gurobipy import *
import pandas as pd
import io

plt.rcParams['savefig.pad_inches'] = 0
st.title('Travelling Salesman Problem')

# Callback - use lazy constraints to eliminate sub-tours
def subtourelim(model, where):
    if where == GRB.Callback.MIPSOL:
        vals = model.cbGetSolution(model._vars)
        selected = tuplelist((i, j) for i, j in model._vars.keys() if vals[i, j] > 0.5)
        
        tour, tours = subtour(selected)
        
        if len(tour) < n:
            model._subtours += 1
            model.cbLazy(quicksum(model._vars[i, j] for i, j in itertools.combinations(tour, 2)) <= len(tour) - 1)

        current_length = round(model.cbGet(GRB.Callback.MIPSOL_OBJ))
        bound = max(0, round(model.cbGet(GRB.Callback.MIPSOL_OBJBND)))
        model._summary.markdown(
            "**Sub-tour elimination constraints:** {:d}  \n**Lower bound:** {:d}km  \n**Current Solution:** {:d}km  - {:d} subtour(s)"
            .format(model._subtours, bound, current_length, len(tours))
        )

        # Plotting the solution
        fig, ax = plt.subplots()
        ax.plot([x[0] for x in points], [x[1] for x in points], 'o')

        for tour in tours:
            tour.append(tour[0])
            points_tour = [points[i] for i in tour]
            ax.plot([x[0] for x in points_tour], [x[1] for x in points_tour], '-')

        ax.set_xlim(0, 105)
        ax.set_ylim(0, 105)
        ax.set_xlabel("km")
        ax.set_ylabel("km")

        model._plot.pyplot(fig)

# Given a tuplelist of edges, find the shortest subtour
def subtour(edges):
    unvisited = list(range(n))
    cycle = range(n+1)
    cycles = []
    
    while unvisited:
        thiscycle = []
        neighbors = unvisited
        while neighbors:
            current = neighbors[0]
            thiscycle.append(current)
            unvisited.remove(current)
            neighbors = [j for i, j in edges.select(current, '*') if j in unvisited]
        
        if len(cycle) > len(thiscycle):
            cycle = thiscycle
        cycles.append(thiscycle)
    
    return cycle, cycles

n = st.slider('How many destinations to generate?', 5, 200, 5)

# Create n random points
points = [(random.randint(0, 100), random.randint(0, 100)) for i in range(n)]

# Dictionary of Euclidean distances between each pair of points
dist = {(i, j): math.sqrt(sum((points[i][k] - points[j][k]) ** 2 for k in range(2)))
        for i in range(n) for j in range(i)}

# Create model
m = Model()
m._subtours = 0
m._summary = st.empty()
m._plot = st.empty()
m._points = points

# Create variables
vars = m.addVars(dist.keys(), obj=dist, vtype=GRB.BINARY, name='e')

# Mirror variables
for i, j in list(vars.keys()):
    vars[j, i] = vars[i, j]

# Add constraints
m.addConstrs(vars.sum(i, '*') == 2 for i in range(n))

# Solve with lazy constraints
m._vars = vars
m.Params.lazyConstraints = 1
m.optimize(subtourelim)

vals = m.getAttr('x', vars)
selected = tuplelist((i, j) for i, j in vals.keys() if vals[i, j] > 0.5)

tour, tours = subtour(selected)
assert len(tour) == n
tour.append(tour[0])
points_tour = [points[i] for i in tour]

# Summary Info
current_length = round(m.objVal)
bound = max(0, round(m.objVal))
m._summary.markdown(
    "**Sub-tour elimination constraints:** {:d}  \n**Lower bound:** {:d}km  \n**Current Solution:** {:d}km  - {:d} subtour(s)"
    .format(m._subtours, bound, current_length, len(tours))
)

# Final Plot
fig, ax = plt.subplots()
ax.plot([x[0] for x in points_tour], [x[1] for x in points_tour], '-o')
for idx, (x, y) in enumerate(points):
    ax.text(x + 1, y + 1, str(idx), fontsize=8)

ax.set_xlim(0, 105)
ax.set_ylim(0, 105)
ax.set_xlabel("km")
ax.set_ylabel("km")

m._plot.pyplot(fig)

# Show stats
st.write('')
st.write('✅ Optimal cost: **{:0.1f}km**'.format(m.objVal))
st.write('⏱️ Running time to optimize: **{:0.1f}s**'.format(m.Runtime))
st.write('🔁 Sub-tour constraints added: **{:d}**'.format(m._subtours))

# ------------------------ NEW ADDITIONS --------------------------

# Distance matrix
dist_matrix = np.zeros((n, n))
for (i, j), d in dist.items():
    dist_matrix[i][j] = dist_matrix[j][i] = d

df = pd.DataFrame(dist_matrix, columns=[f"P{j}" for j in range(n)], index=[f"P{i}" for i in range(n)])

st.subheader("📊 Distance Matrix (Euclidean Distance in km)")
st.dataframe(df.style.background_gradient(cmap='Blues'), height=400)

# Download button for distance matrix
csv = df.to_csv(index=True)
b64 = csv.encode()

st.download_button(
    label="📥 Download Distance Matrix as CSV",
    data=b64,
    file_name="distance_matrix.csv",
    mime='text/csv'
)
