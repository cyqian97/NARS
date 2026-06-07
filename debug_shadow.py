import matplotlib.pyplot as plt
import numpy as np

gap_vertex = (24.4482, 29.7349)
dx, dy = 0.3209899268131231, 18.213498595762836
edge_p1 = (24.473650000000013, 30.830739999999984)
edge_p2 = (24.478050000000014, 31.926439999999985)

length = np.hypot(dx, dy)
ndx, ndy = dx / length, dy / length

ray_length = 2.0
ray_end = (gap_vertex[0] + ndx * ray_length, gap_vertex[1] + ndy * ray_length)

fig, ax = plt.subplots(figsize=(8, 8))

# Forward ray
ax.annotate('', xy=ray_end, xytext=gap_vertex,
            arrowprops=dict(arrowstyle='->', color='steelblue', lw=1.5))

# Edge
ax.plot([edge_p1[0], edge_p2[0]], [edge_p1[1], edge_p2[1]],
        color='orangered', lw=2, marker='o', markersize=5, label='edge')
ax.annotate('p1', edge_p1, textcoords='offset points', xytext=(5, -10), fontsize=8)
ax.annotate('p2', edge_p2, textcoords='offset points', xytext=(5, 5),  fontsize=8)

# Gap vertex
ax.plot(*gap_vertex, 'k*', markersize=12, label='gap_vertex')
ax.annotate('gap_vertex', gap_vertex, textcoords='offset points', xytext=(5, -12), fontsize=8)

ax.invert_yaxis()
plt.axis('equal')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_title('Shadow ray vs edge')
plt.tight_layout()
plt.savefig('debug_shadow.png', dpi=150)
print('Saved debug_shadow.png')
plt.show()
